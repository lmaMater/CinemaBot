from os import getenv
import aiohttp
from dotenv import load_dotenv

from exceptions import CinemaBotException

load_dotenv()

# VK, KP
VK_TOKEN = getenv('VK_TOKEN')
KP_TOKEN = getenv('KP_TOKEN')
if not VK_TOKEN or not KP_TOKEN:
    raise ValueError("Не достает токенов! Пинганите автора tg: @lmaMater или поднимите самостоятельно")


class MovieSearcher():
    def __init__(self, base_request: str, session: aiohttp.ClientSession):
        self.base_request = f'{base_request.strip()} '
        self.vk_base_url = 'https://api.vk.com/method/video.search'
        self.ddg_url = 'https://api.duckduckgo.com/'
        self.kinopoisk_url = 'https://www.kinopoisk.ru/'
        self.kinopoisk_api_url = 'https://api.kinopoisk.dev/v1.4/movie/search'

        self.session = session

    async def fetch_vk_reference(self, request: str, count=1, vk_sort=0, filters='long,vk', vk_version='5.199'):
        if not request.strip():
            raise CinemaBotException('Request should not be empty!')

        params = {
            'q': f'{self.base_request} {request}',
            'count': count,
            'access_token': VK_TOKEN,
            'v': vk_version,
            'filters': filters,
            'sort': vk_sort
            }

        async with self.session.get(self.vk_base_url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"Error": f"API запрос упал со статусом  {response.status}"}

    async def get_kp_info_json(self, query: str):
        '''
        Returns formatted string with movie's info and description
        '''
        params = {
            'page': 1,
            'limit': 1,
            'query': query,
            'token': KP_TOKEN
        }
        async with self.session.get(self.kinopoisk_api_url, params=params) as response:
            if response.status == 200:
                json_response = await response.json()
                if not json_response['docs']:
                    raise CinemaBotException('ничего не найдено :(')
                return json_response['docs'][0]
            else:
                return {"Error": f"API запрос упал со статусом {response.status}"}

    async def get_info(self, query: str):
        '''
        Returns movie info
        '''
        json_data = await self.get_kp_info_json(query)

        info = {
            'title': json_data['name'],
            'year': json_data['year'],
            'length': json_data['movieLength'],
            'description': ' '.join(json_data['description'].split('\xa0')),
            'kp': json_data['rating']['kp'],
            'imdb': json_data['rating']['imdb'],
            'image_url': json_data['poster']['url']
        }

        return info

    async def get_references(self, query: str):
        '''
        Returns list of tuples (title, reference)
        '''
        response = await self.fetch_vk_reference(query, count=50)
        if 'response' in response and 'items' in response['response']:
            return [(item['title'], item['player']) for item in response['response']['items']]
        else:
            return []


async def main():
    async with aiohttp.ClientSession() as session:
        request = 'venom'
        ms = MovieSearcher(request, session)
        print(await ms.fetch_vk_reference(request))

        for elem in await ms.get_references(request):
            print(elem)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
