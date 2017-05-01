from urllib.parse import urljoin

import requests
from django.http import HttpResponse
from rest_framework.views import APIView


THEMOVIEDB = {
    'base_url': 'https://api.themoviedb.org',
    'api_version': 3,
    'api_key': '9afa0e79416498e0b552082c88b29f25',
}


VK = {
    'community_access_token': '313d1b9184a3e65fb7ed316019e4adee167d8b8427c577d5a75ce7d0c2a08b356ce7bb9a43ec33dbc9f1a',
    'send_message_api_url': 'https://api.vk.com/method/messages.send',
    'bot_view_confirmation_code': '6bbb32e8',
}


class MovieDbClient:

    def __init__(self):
        self.api_url = THEMOVIEDB['base_url']

    def get(self, url_path, params):
        full_url = urljoin(self.api_url, '{}/{}'.format(THEMOVIEDB['api_version'], url_path))
        payload = {'api_key': THEMOVIEDB['api_key']}
        payload.update(params)
        resp = requests.get(full_url, params=payload)
        return resp.json()

    def search(self, query):
        resp = self.get('search/tv', params={'query': query})
        return resp['results']


class VkMessenger:
    def __init__(self):
        self.access_token = VK['community_access_token']
        self.api_url = VK['send_message_api_url']

    def send_message(self, user_id, message):
        return requests.post(self.api_url, data={
                'access_token': self.access_token,
                'user_id': user_id,
                'message': message})


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
        else:
            message = 'Invalid command "{}". Available commands are: "search"'.format(command)
            self.send_message(message)

    def search(self, query):
        serials = self.movie_client.search(query)

        if not serials:
            self.send_message(
                message='Nothing found with '"{}"', try with another search query.'.format(query))

        resp_message = ''
        for i, tv in enumerate(serials, 1):
            resp_message += '{number}. {name}, {year}\n'.format(
                    number=i,
                    name=tv['name'],
                    year=tv['first_air_date'].split('-', 1)[0])

            if tv['original_name'] != tv['name']:
                resp_message = resp_message.replace('\n', '({})\n'.format(tv['original_name']))
        self.send_message(resp_message)

    def send_message(self, message):
        return self.vk_client.send_message(user_id=self.user_id, message=message)

