from django.http import HttpResponse
from rest_framework.views import APIView

from common.models import VkUser, TVSeriesVariants, TVSeries
from common.themoviedb_client import MovieDbClient
from common.vk_client import VK, VkMessenger


class HandleVkRequestView(APIView):

    COMMAND_HANDLERS = {
        'search_tv': {
            'commands': ['search', '-s'],
            'argument_required': True,
            'argument_name': 'query',
            'doc': 'Allow to search TV-shows by title',
        },
        'add_tv': {
            'commands': ['add', '-a'],
            'argument_required': True,
            'argument_name': 'number',
            'doc': 'Allow to add TV-show to your list after search. '
                   'Usage: add <number_in_last_search_results>',
        },
        'get_users_tv_shows': {
            'commands': ['list', '-l'],
            'argument_required': False,
            'doc': 'Show list of all added TV-shows.',
        },
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.movie_client = MovieDbClient()
        self.vk_client = VkMessenger()

    def post(self, request, *args, **kwargs):
        event_type = request.data['type']

        if event_type == 'confirmation':
            return HttpResponse(VK['bot_view_confirmation_code'])

        event_data = request.data['object']
        self.user_id = event_data['user_id']
        self.vk_user, created = VkUser.objects.get_or_create(vk_id=self.user_id)

        if event_type == 'message_new':
            self.message_new(event_data)
        else:
            print('SOME EVENT: ', event_type)
        return HttpResponse('ok', status=200)

    def message_new(self, event_data):
        message_text = event_data['body']
        if len(message_text.split()) > 1:
            command, arguments = message_text.split(' ', 1)
        else:
            command, arguments = message_text, None

        for handler, params in self.COMMAND_HANDLERS.items():
            if command in params['commands']:
                if not params['argument_required']:
                    return getattr(self, handler)()

                if not arguments:
                    return self.send_message(
                        'Argument "{}" is required for command "{}"'.format(
                                params['argument_name'], command))

                return getattr(self, handler)(arguments)

        all_commands_str = ', '.join(['{} ({})'.format(
                c['commands'][0], c['commands'][1]) for c in self.COMMAND_HANDLERS.values()])
        return self.send_message(
                'Invalid command "{}". Available commands are: {}'.format(
                        command, all_commands_str))

    def search_tv(self, query):
        serials = self.movie_client.search(query)

        if not serials:
            self.send_message(
                message='Nothing found with '"{}"', try with another search query.'.format(query))

        series_variants_dict = {}

        resp_message = ''
        for i, tv in enumerate(serials, 1):
            series_variants_dict[i] = tv
            resp_message += '{number}. {name}, {year}\n'.format(
                    number=i,
                    name=tv['name'],
                    year=tv['first_air_date'].split('-', 1)[0])

            if tv['original_name'] != tv['name']:
                resp_message = resp_message.replace('\n', '({})\n'.format(tv['original_name']))
        self.send_message(resp_message)

        TVSeriesVariants.objects.get_or_create(vk_user=self.vk_user, variants=series_variants_dict)

    def add_tv(self, number):
        tv_variants = TVSeriesVariants.objects.filter(vk_user=self.vk_user).latest('created')
        if not tv_variants:
            return self.send_message('You have to search first')

        if number not in tv_variants.variants.keys():
            return self.send_message('Invalid number "{}", valid variant are: {}'.format(
                    number,  ', '.join(tv_variants.variants.keys())))

        tv_series_data = tv_variants.variants[number]
        tv_series, created = TVSeries.objects.get_or_create(
                themoviedb_id=tv_series_data['id'],
                name=tv_series_data['name'],
                original_name=tv_series_data['original_name'])

        if tv_series_data['first_air_date']:
            tv_series.first_air_date = tv_series_data['first_air_date']
            tv_series.save()

        self.vk_user.tv_series.add(tv_series)
        return self.send_message('TV-show "{}" was added to your list.'.format(tv_series.name))

    def get_users_tv_shows(self):
        tv_shows_list_str = ''
        for i, tv_show in enumerate(self.vk_user.tv_series.order_by('id'), 1):
            tv_shows_list_str += '{}. {}\n'.format(i, str(tv_show))
        if tv_shows_list_str:
            self.send_message(tv_shows_list_str)
        else:
            self.send_message('You don\'t have any added TV-shows')

    def send_message(self, message):
        return self.vk_client.send_message(user_id=self.user_id, message=message)

