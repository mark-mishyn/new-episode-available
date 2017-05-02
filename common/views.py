from django.http import HttpResponse
from rest_framework.views import APIView

from clock import update_tv_shows_info
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
        'update_tv_shows_info': {
            'commands': ['update', '-u'],
            'argument_required': False,
            'doc': 'Update information for all added TV-shows.',
        },
        'remove_tv_show': {
            'commands': ['remove', '-r'],
            'argument_required': True,
            'argument': 'number or \'all\'',
            'doc': 'Remove all TV-shows from your list or all TV-shows.',
        },
    }

    EMPTY_TV_SHOWS_MESSAGE = 'You don\'t have any added TV-shows'

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
                    return self._send_message(
                        'Argument "{}" is required for command "{}"'.format(
                                params['argument_name'], command))

                return getattr(self, handler)(arguments)

        all_commands_str = ', '.join(['{} ({})'.format(
                c['commands'][0], c['commands'][1]) for c in self.COMMAND_HANDLERS.values()])
        return self._send_message(
                'Invalid command "{}". Available commands are: {}'.format(
                        command, all_commands_str))

    def search_tv(self, query):
        serials = self.movie_client.search(query)

        if not serials:
            self._send_message(
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
        self._send_message(resp_message)

        TVSeriesVariants.objects.get_or_create(vk_user=self.vk_user, variants=series_variants_dict)

    def add_tv(self, number):
        tv_variants = TVSeriesVariants.objects.filter(vk_user=self.vk_user).latest('created')
        if not tv_variants:
            return self._send_message('You have to search first')

        if number not in tv_variants.variants.keys():
            return self._send_message('Invalid number "{}", valid variant are: {}'.format(
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
        return self._send_message('TV-show "{}" was added to your list.'.format(tv_series.name))

    def get_users_tv_shows(self):
        tv_shows_list_str = self._get_tv_shows_list_str()
        if tv_shows_list_str:
            self._send_message(tv_shows_list_str)
        else:
            self._send_message(self.EMPTY_TV_SHOWS_MESSAGE)

    def update_tv_shows_info(self):
        if not self.vk_user.tv_series.exists():
            return self._send_message(self.EMPTY_TV_SHOWS_MESSAGE)

        self._send_message('Updating information...')
        update_tv_shows_info()
        self._send_message('Updated list of TV-shows: \n{}'.format(self._get_tv_shows_list_str()))

    def remove_tv_show(self, number_or_all):
        if number_or_all == 'all':
            self.vk_user.tv_series.all().delete()
            return self._send_message('All TV-shows was removed.')

        try:
            number = int(number_or_all)
        except (ValueError, TypeError):
            return self._send_message('Invalid number.')

        try:
            tv_show = self.vk_user.tv_series.order_by('id')[number - 1]
            tv_show_name = tv_show.name
            tv_show.delete()
        except IndexError:
            self._send_message('Invalid number.')
        else:
            self._send_message('TV-show "{}" was removed.'.format(tv_show_name))

    def _send_message(self, message):
        return self.vk_client.send_message(user_id=self.user_id, message=message)

    def _get_tv_shows_list_str(self):
        tv_shows_list_str = ''
        for i, tv_show in enumerate(self.vk_user.tv_series.order_by('id'), 1):
            tv_shows_list_str += '{}. {}\n'.format(i, str(tv_show))
        return tv_shows_list_str
