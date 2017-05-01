import requests

VK = {
    'community_access_token': '313d1b9184a3e65fb7ed316019e4adee167d8b8427c577d5a75ce7d0c2a08b356ce7bb9a43ec33dbc9f1a',
    'send_message_api_url': 'https://api.vk.com/method/messages.send',
    'bot_view_confirmation_code': '6bbb32e8',
}


class VkMessenger:
    def __init__(self):
        self.access_token = VK['community_access_token']
        self.api_url = VK['send_message_api_url']

    def send_message(self, user_id, message):
        return requests.post(self.api_url, data={
                'access_token': self.access_token,
                'user_id': user_id,
                'message': message})
