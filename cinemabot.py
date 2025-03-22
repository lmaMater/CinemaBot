import asyncio
import logging
import sys
import time
from os import getenv
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from movie_searcher import MovieSearcher
from rapidfuzz import process

from exceptions import CinemaBotException
from db_manager import DBManager


load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")
VK_TOKEN = getenv("VK_TOKEN")

if not BOT_TOKEN or not VK_TOKEN:
    raise ValueError("BOT_TOKEN or VK_TOKEN not found in environment variables!")

dp = Dispatcher()
db = DBManager()


async def start_bot():
    async with aiohttp.ClientSession() as session:
        movie_searcher = MovieSearcher(base_request='фильм', session=session)

        @dp.message(Command('start'))
        async def command_start_handler(message: Message) -> None:
            await message.answer('Привет! Напиши название фильма, а я найду его для тебя.\nНажмите /help чтобы посмотреть команды')

        @dp.message(Command('history'))
        async def command_history_handler(message: Message) -> None:
            user_id = str(message.from_user.id)
            history = db.get_search_history(user_id)
            if not history:
                await message.answer("История поиска пуста.")
                return

            response = "История поиска:\n" + "\n".join(
                f"{query} → {movie}" for query, movie in history
            )
            await message.answer(response)

        @dp.message(Command('stats'))
        async def command_stats_handler(message: Message) -> None:
            user_id = str(message.from_user.id)
            stats = db.get_movie_stats(user_id)
            if not stats:
                await message.answer("Статистика пустая.")
                return

            response = "Статистика фильмов:\n" + "\n".join(
                f"{movie} - {count} раз(а)" for movie, count in stats
            )
            await message.answer(response)

        @dp.message(Command('help'))
        async def command_help_handler(message: Message) -> None:
            help_text = '''
Доступные команды:
/start - Начать работу с ботом
/help - Справка
название_фильма - Найти фильм и информацию о нем
/history - Показать историю поиска фильмов
/stats - Показать статистику фильмов'''
            await message.answer(help_text)

        @dp.message()
        async def movie_search_handler(message: Message) -> None:
            user_id = str(message.from_user.id)
            user_input = message.text.strip()
            if not user_input:
                await message.answer('Пожалуйста, напиши название фильма.')
                return

            await message.answer(f'Ищу фильм: {user_input}...')
            start_time = time.time()
            try:
                response_message = ''

                movie_info_dict = await movie_searcher.get_info(user_input)
                
                if not movie_info_dict['title']:
                    raise CinemaBotException('ничего не найдено :(')
                movie_info = f'<b>{movie_info_dict['title']} ({movie_info_dict['year']})</b>\n'
                if movie_info_dict['length']:
                    movie_info += f'{movie_info_dict['length'] // 60}h {movie_info_dict['length'] % 60}m\n\n'
                movie_description = " ".join(movie_info_dict['description'].split('\xa0'))
                movie_info += f'{movie_description[:500]}{"..." if len(movie_description) > 500 else ""}\n\n'
                if movie_info_dict['kp'] != 0:
                    movie_info += f'Кинопоиск: <i>{movie_info_dict['kp']}</i>\n'
                if movie_info_dict['imdb'] != 0:
                    movie_info += f'IMDB: <i>{movie_info_dict['imdb']}</i>\n'

                movie_references = ''
                movie_title = f'{movie_info_dict['title']} ({movie_info_dict['year']})'
                db.save_search(user_id, user_input, movie_title)
                db.increment_movie_stat(user_id, movie_title)

                references = await movie_searcher.get_references(movie_title)
                best_match = process.extractOne(
                    movie_title,
                    [title for title, _ in references]
                )
                if best_match:
                    best_title = best_match[0]
                    best_url = next(url for title, url in references if title == best_title)
                    movie_references = f'<a href="{best_url}">{best_title}</a>\n'

                elapsed_time = time.time() - start_time
                response_message = f'''
{movie_info}
{movie_references}
Время поиска: {elapsed_time:.2f}с. Приятного просмотра!'''

                if 'image_url' in movie_info_dict and movie_info_dict['image_url']:
                    try:
                        await message.answer_photo(
                            photo=movie_info_dict['image_url'],
                            caption=response_message,
                        )
                    except Exception as e:
                        await message.answer(f'Ошибка при отправке изображения: {e}\n{response_message}')
                else:
                    await message.answer(response_message)

            except Exception as e:
                await message.answer(f'Ошибка при поиске: {e}')

        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
        await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(start_bot())
