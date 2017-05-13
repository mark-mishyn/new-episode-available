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
            'argument_name': 'search_query',
            'doc': 'Allow to search TV-shows by title.',
        },
        'add_tv': {
            'commands': ['add', '-a'],
            'argument_required': True,
            'argument_name': 'number_in_last_search_results',
            'doc': 'Allow to add TV-show to your list after search.'
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
            'argument_name': '\'all\' OR number_in_shows_list',
            'doc': 'Remove TV-show from your list or all TV-shows.',
        },
        'get_help': {
            'commands': ['help', '-h'],
            'argument_required': False,
            'doc': 'Show this message.',
        },
    }

    EMPTY_TV_SHOWS_MESSAGE = 'You don\'t have any added TV-shows'
    WELCOME_MESSAGE = ('Use "search" command to find TV-shows and then "add" to add TV-shows to '
                       'your list and start receiving notifications when new episodes of your '
                       'favourite TV-series are available!')

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
        self.vk_user, is_new_user = VkUser.objects.get_or_create(vk_id=self.user_id)

        if is_new_user:
            self._send_message(
                'Hello!\n' + self.WELCOME_MESSAGE + '\nSend message with text "help" to get help.')
        elif event_type == 'message_new':
            self.message_new(event_data)
        else:
            print(event_type)
            print(event_data)

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
                    resp_massage = getattr(self, handler)()
                    return self._send_message(resp_massage)

                if not arguments:
                    return self._send_message(
                        'Argument "{}" is required for command "{}"'.format(params['argument_name'],
                                                                            command))

                resp_massage = getattr(self, handler)(arguments)
                return self._send_message(resp_massage)

        all_commands_str = ', '.join(['{} ({})'.format(
                c['commands'][0], c['commands'][1]) for c in self.COMMAND_HANDLERS.values()])
        return self._send_message(
                'Invalid command "{}". Available commands are: {}'.format(command,
                                                                          all_commands_str))

    def search_tv(self, query):
        serials = self.movie_client.search(query)

        if not serials:
            return 'Nothing found with '"{}"', try with another search query.'.format(query)

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

        TVSeriesVariants.objects.create(vk_user=self.vk_user, variants=series_variants_dict)

        return resp_message

    def add_tv(self, number):
        tv_variants = TVSeriesVariants.objects.filter(vk_user=self.vk_user).latest('created')
        if not tv_variants:
            return 'You have to search first'

        variant_numbers = tv_variants.variants.keys()
        if number not in variant_numbers:
            variant_numbers = [int(n) for n in tv_variants.variants.keys()]
            if len(variant_numbers) == 1:
                valid_numbers = variant_numbers[0]
            elif len(variant_numbers) == 2:
                valid_numbers = '{}, {}'.format(min(variant_numbers), max(variant_numbers))
            else:
                valid_numbers = '{}-{}'.format(min(variant_numbers), max(variant_numbers))

            return 'Invalid number "{}", valid variants are: {}'.format(number,  valid_numbers)

        tv_series_data = tv_variants.variants[number]
        tv_series, created = TVSeries.objects.get_or_create(
                themoviedb_id=tv_series_data['id'],
                name=tv_series_data['name'],
                original_name=tv_series_data['original_name'])

        if tv_series_data['first_air_date']:
            tv_series.first_air_date = tv_series_data['first_air_date']
            tv_series.save()

        tv_series.update_last_available_episode_date()

        self.vk_user.tv_series.add(tv_series)
        return 'TV-show "{}" was added to your list.'.format(tv_series.name)

    def get_users_tv_shows(self):
        tv_shows_list_str = self._get_tv_shows_list_str()
        if not tv_shows_list_str:
            return self.EMPTY_TV_SHOWS_MESSAGE

        return tv_shows_list_str

    def update_tv_shows_info(self):
        if not self.vk_user.tv_series.exists():
            return self.EMPTY_TV_SHOWS_MESSAGE

        self._send_message('Updating information...')
        for tv in TVSeries.objects.filter(vk_users=self.vk_user):
            tv.update_last_available_episode_date()
        return 'Updated list of TV-shows: \n{}'.format(self._get_tv_shows_list_str())

    def remove_tv_show(self, number_or_all):
        if number_or_all == 'all':
            self.vk_user.tv_series.all().delete()
            return 'All TV-shows was removed.'

        try:
            number = int(number_or_all)
        except (ValueError, TypeError):
            return 'Invalid number.'

        try:
            tv_show = self.vk_user.tv_series.order_by('id')[number - 1]
            tv_show_name = tv_show.name
            tv_show.delete()
        except IndexError:
            return 'Invalid number.'
        else:
            return 'TV-show "{}" was removed.'.format(tv_show_name)

    def get_help(self):
        resp_message = self.WELCOME_MESSAGE + '\n'

        for handler in self.COMMAND_HANDLERS.values():
            resp_message += '({}) {}'.format(handler['commands'][1], handler['commands'][0])
            if handler['argument_required']:
                resp_message += ' {}'.format(handler['argument_name'])
            resp_message += ' - {} \n'.format(handler['doc'])

        return resp_message

    def _send_message(self, message):
        return self.vk_client.send_message(user_id=self.user_id, message=message)

    def _get_tv_shows_list_str(self):
        tv_shows_list_str = ''
        for i, tv_show in enumerate(self.vk_user.tv_series.order_by('id'), 1):
            tv_shows_list_str += '{}. {} \n \n'.format(i, str(tv_show))
        return tv_shows_list_str
