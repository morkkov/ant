import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
import time

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_logs.log"),
        logging.StreamHandler()
    ]
)

# Telegram bot token
API_TOKEN = '8166286788:AAHziecCZi_W-z7MzwLZOjqJUocyX-mZK5w'

# Создаем объект бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Путь к драйверу Chrome
chrome_driver_path = r'/usr/bin/chromedriver'

# Хранение ID обработанных объявлений
processed_ads = set()
user_urls = {}
driver = None

# Инициализация драйвера
def init_driver():
    global driver
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = "/usr/bin/chromium-browser"

        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("Драйвер успешно запущен.")
    except Exception as e:
        logging.error(f"Ошибка при инициализации драйвера: {e}")
        raise

# Получение новых объявлений
def get_first_vinted_item(user_url):
    global driver
    try:
        driver.get(user_url)
        logging.info(f"Открыта страница: {user_url}")
        time.sleep(5)

        items = []
        ads = driver.find_elements(By.CLASS_NAME, 'feed-grid__item-content')

        if ads:
            ad = ads[0]
            try:
                title = ad.find_element(By.CLASS_NAME, 'web_ui__Text__truncated').text
                price = ad.find_element(By.CLASS_NAME, 'web_ui__Text__underline-none').text
                link_element = ad.find_element(By.CLASS_NAME, 'new-item-box__overlay--clickable')
                link_url = link_element.get_attribute("href")
                size_info = link_element.get_attribute("title")

                ad_parent = ad.find_element(By.CLASS_NAME, 'web_ui__Image__ratio')
                img_tag = ad_parent.find_element(By.CLASS_NAME, 'web_ui__Image__content')
                image_url = img_tag.get_attribute("src")

                ad_id = f"{title} - {price}"

                if ad_id not in processed_ads:
                    items.append({
                        "title": title,
                        "price": price,
                        "url": link_url,
                        "size": size_info,
                        "image_url": image_url
                    })
                    processed_ads.add(ad_id)
                    logging.info(f"Новое объявление: {ad_id}")
            except Exception as e:
                logging.error(f"Ошибка при обработке объявления: {e}")
        else:
            logging.info("Объявлений не найдено.")
        return items

    except Exception as e:
        logging.error(f"Ошибка при получении данных с Vinted: {e}")
        return []

# Фоновый мониторинг объявлений
async def monitor_vinted_updates(user_id, user_url):
    while True:
        try:
            logging.info(f"Начало мониторинга для пользователя {user_id}. URL: {user_url}")
            items = await asyncio.to_thread(get_first_vinted_item, user_url)

            if items:
                for item in items:
                    title = item.get("title", "Без названия")
                    price = item.get("price", "Цена не указана")
                    link = item.get("url", "Нет ссылки")
                    size = item.get('size', 'нет сайза')
                    image_url = item.get('image_url', 'Нет изображения')

                    response_text = f"Товар: {title}\nЦена: {price}\nРазмер: {size}\nСсылка: {link}\nИзображение: {image_url}"

                    try:
                        await bot.send_message(chat_id=user_id, text=response_text)
                        logging.info(f"Сообщение отправлено пользователю {user_id}: {response_text}")
                    except Exception as e:
                        logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

            await asyncio.sleep(600)
        except Exception as e:
            logging.error(f"Ошибка в мониторинге для пользователя {user_id}: {e}")
            await asyncio.sleep(10)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_monitoring(message: types.Message):
    user_id = message.chat.id

    if not os.path.exists("users.txt"):
        open("users.txt", "w").close()

    try:
        with open("users.txt", "r") as file:
            existing_users = file.read().splitlines()

        if str(user_id) not in existing_users:
            with open("users.txt", "a") as file:
                file.write(f"{user_id}\n")
            logging.info(f"Добавлен новый пользователь: {user_id}")

        await message.reply("Бот запущен. Отправьте команду /seturl <ссылка>, чтобы установить ссылку для мониторинга.")
    except Exception as e:
        logging.error(f"Ошибка записи ID пользователя: {e}")
        await message.reply("Ошибка при сохранении вашего ID. Попробуйте позже.")

# Обработчик команды /seturl
@dp.message_handler(commands=['seturl'])
async def set_url(message: types.Message):
    user_id = message.chat.id
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.reply("Пожалуйста, укажите ссылку. Пример: /seturl <ссылка>")
        return

    user_url = args[1]
    user_urls[user_id] = user_url
    logging.info(f"Пользователь {user_id} установил URL: {user_url}")

    await message.reply("Ссылка установлена. Бот начнет мониторинг.")
    asyncio.create_task(monitor_vinted_updates(user_id, user_url))

# Запуск бота
if __name__ == '__main__':
    try:
        init_driver()
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logging.critical(f"Критическая ошибка запуска бота: {e}")
