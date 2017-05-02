from urllib.parse import urljoin

import requests

THEMOVIEDB = {
    'base_url': 'https://api.themoviedb.org',
    'api_version': 3,
    'api_key': '9afa0e79416498e0b552082c88b29f25',
}


class MovieDbClient:

    def __init__(self):
        self.api_url = THEMOVIEDB['base_url']

    def get(self, url_path, params=None):
        payload = {'api_key': THEMOVIEDB['api_key']}
        if params:
            payload.update(params)
        full_url = urljoin(self.api_url, '{}/{}'.format(THEMOVIEDB['api_version'], url_path))
        resp = requests.get(full_url, params=payload)
        return resp.json()

    def search(self, query):
        resp = self.get('search/tv', params={'query': query})
        return resp['results']

    def get_details(self, tv_id):
        return self.get('/tv/{}'.format(tv_id))

    def get_season_details(self, tv_id, season_id):
        return self.get('/tv/{}/season/{}'.format(tv_id, season_id))
