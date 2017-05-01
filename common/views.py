from django.http import HttpResponse
from rest_framework.views import APIView

from common.models import VkUser, TVSeriesVariants, TVSeries
from common.themoviedb_client import MovieDbClient
from common.vk_client import VK, VkMessenger


class HandleVkRequestView(APIView):

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
            command, arguments = message_text, ''

        if (command == 'search') and arguments:
            self.search(arguments)
        elif (command == 'add') and arguments:
            self.add_tv(arguments)
        else:
            message = 'Invalid command "{}". Available commands are: "search", "add"'.format(
                    command)
            self.send_message(message)

    def search(self, query):
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
                original_name=tv_series_data['original_name'],
                first_air_date=tv_series_data['first_air_date'])
        self.vk_user.tv_series.add(tv_series)
        return self.send_message('TV-show {} was added to your list.'.format(tv_series.name))

    def send_message(self, message):
        return self.vk_client.send_message(user_id=self.user_id, message=message)

