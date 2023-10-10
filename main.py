import logging
import time
import traceback
from datetime import datetime

import openai
import asyncio
import spacy

from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions
from config import API_KEYS, BOT_KEYS, ID, MAX_MESSAGE_LENGTH
from faq import faq

# Языковая модель для spacy (en_core_web_sm или ru_core_news_sm)
nlp = spacy.load("ru_core_news_sm")

# Создаем логгер и устанавливаем уровень логирования
logging.basicConfig(filename='bot.log', level=logging.INFO)

# Устанавливаем API-ключ OpenAI и экземпляр бота TG с токеном
openai.api_key = API_KEYS
bot = Bot(token=BOT_KEYS)

# Инициализируем диспетчер для обработки входящих сообщений
dp = Dispatcher(bot)

# переменная для хранения массива сообщений и их ролей
messages_history = []


# Обработчик команды /log для получения лог-файла
@dp.message_handler(commands=['log'])
async def send_log_button(message: types.Message):
    user_id = ID
    if message.from_user.id == user_id:
        with open('bot.log', 'rb') as f:
            await bot.send_document(user_id, f)
    else:
        await message.answer("У вас нет доступа к этой команде.")


# Обработчик команды /clear_log для очистки лог-файла
@dp.message_handler(commands=['clear_log'])
async def clear_log(message: types.Message):
    user_id = ID
    if message.from_user.id == user_id:
        open('bot.log', 'w').close()
        await message.answer("Файл логов очищен.")
    else:
        await message.answer("У вас нет доступа к этой команде.")


# Обработчик команды /help для очистки лог-файла
@dp.message_handler(commands=['help'])
async def help_button(message: types.Message):
    await message.answer(faq)


@dp.message_handler(commands=['clear'])
async def clear_history_button(message: types.Message):
    global messages_history
    messages_history = []
    await message.answer("🗑 История чата очищена. Можете задать новый вопрос.")


# Функция разбивки текста на части
def split_text(text, max_length):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


# Приветственное сообщение
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет!\n\n\nЯ бот, который может отвечать на вопросы по разным темам.\nПросто задай мне свой "
                        "вопрос и я постараюсь дать на него ответ.\n\nДля того, чтобы очистить историю сообщений ("
                        "контекста прошлых вопросов), используй команду /clear, что позволит ChatGPT начать общение "
                        "на новую тему \n\n\nБот постоянно улучшается, но было бы круто, если бы вы "
                        "поделились обратной связью @Safronjack")


# Функция, которая обрабатывает сообщение и отправляет ответ пользователю
async def handle_message(message: types.Message):
    global messages_history
    start_time = time.time()  # запоминаем время начала обработки запроса
    processing_message = await message.answer("⏳ Обрабатываем ваш вопрос. Это может занять некоторое время.")
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # Обработка контекста с помощью spacy для определения ключевых слов и фраз в запросе пользователя
        doc = nlp(message.text)
        entities = []
        for ent in doc.ents:
            entities.append((ent.text, ent.label_))
        messages_history.append({"role": "user", "content": message.text})
        response = openai.api_resources.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages_history,
            stop=None,
            temperature=0.4,
            stream=False
        )

        text = response.choices[0].message.content
        messages_history.append({"role": "assistant", "content": text})

        # Разбиваем ответ на части, если он слишком длинный
        if len(text) > MAX_MESSAGE_LENGTH:
            text_parts = split_text(text, MAX_MESSAGE_LENGTH)
            for part in text_parts:
                await message.answer(part)
        else:
            await message.answer(text)

    except openai.error.RateLimitError as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ Вы отправляете слишком много запросов. Попробуйте повторить через 30 секунд.")
    except openai.error.InvalidRequestError as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ Превышен лимит токенов отправляемых к API. Для модели GPT 3.5 turbo максимум 4097 токенов. Очистите "
            "историю командой /clear. Подробная информация в FAQ")
    except IndexError as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ К сожалению, не удалось получить ответ от API. Попробуйте повторить запрос позже.")
    except KeyError as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ Непредвиденная ошибка. Очистите историю командой /clear и попробуйте повторить запрос заново.")
    except TypeError as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ Непредвиденная ошибка. Очистите историю командой /clear и попробуйте повторить запрос заново.")
    except spacy.errors.Errors as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ К сожалению, произошла ошибка при обработке вашего запроса. Попробуйте повторить позже.")
    except exceptions.NetworkError as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ К сожалению, Telegram API не отвечает. Попробуйте повторить позже.")
    except ConnectionError as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ К сожалению, Telegram API не отвечает. Попробуйте повторить позже.")
    except exceptions.BadRequest as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ Вы ввели неккоректный запрос. Очистите историю командой /clear и попробуйте повторить запрос заново.")
    except exceptions.Unauthorized as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ Критическая ошибка бота. Просьба связаться с @Safronjack.")
    except Exception as e:
        tb = traceback.format_exc()
        logging.exception(f"{datetime.now()} - {tb}")
        await message.answer(
            "❌ К сожалению, произошла ошибка при обработке вашего запроса. Попробуйте повторить позже.")

    finally:
        await processing_message.delete()

        # вычисляем время обработки запроса и логируем его
        end_time = time.time()
        elapsed_time = end_time - start_time
        logging.info(f"{datetime.now()} - @User {message.from_user.id}: {message.text} \n{elapsed_time:.3f} sec.")


# Отвечает на сообщения, используя API ChatGPT
@dp.message_handler()
async def send_reply(message: types.Message):
    asyncio.create_task(handle_message(message))


if __name__ == '__main__':
    asyncio.run(dp.start_polling())
