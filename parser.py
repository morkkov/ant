import asyncio
import logging
import os
import time
from aiogram import Bot, Dispatcher, executor, types
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)

# Telegram bot token
API_TOKEN = 'Ваш_токен_здесь'  # Замените на ваш токен

# Создаем объект бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Путь к драйверу Chrome
CHROME_DRIVER_PATH = r'/полный/путь/к/chromedriver'

# Хранение ID обработанных объявлений
processed_ads = set()
user_urls = {}

# Инициализация драйвера
def init_driver():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = "/usr/bin/chromium-browser"  # Укажите путь к браузеру Chrome

        service = Service(CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("Драйвер успешно инициализирован.")
        return driver
    except Exception as e:
        logging.critical(f"Ошибка при инициализации драйвера: {e}")
        raise

# Получение новых объявлений
def get_first_vinted_item(driver, user_url):
    logging.info(f"Начало обработки URL: {user_url}")
    driver.get(user_url)
    time.sleep(5)
    items = []

    try:
        ads = driver.find_elements(By.CLASS_NAME, 'feed-grid__item-content')
        if ads:
            ad = ads[0]  # Обрабатываем только первое объявление
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
                    logging.info(f"Новое объявление: {title}, {price}")
                else:
                    logging.info("Объявление уже обработано.")
            except Exception as e:
                logging.error(f"Ошибка при обработке объявления: {e}")
    except Exception as e:
        logging.error(f"Ошибка при получении объявлений: {e}")

    return items

# Фоновый мониторинг объявлений
async def monitor_vinted_updates(user_id, user_url, driver):
    while True:
        items = await asyncio.to_thread(get_first_vinted_item, driver, user_url)

        if items:
            for item in items:
                title = item.get("title", "Без названия")
                price = item.get("price", "Цена не указана")
                link = item.get("url", "Нет ссылки")
                size = item.get('size', 'Нет размера')
                image_url = item.get('image_url', 'Нет изображения')

                response_text = f"Товар: {title}\nЦена: {price}\nРазмер: {size}\nИзображение: {image_url}\nСсылка: {link}"

                try:
                    await bot.send_message(chat_id=user_id, text=response_text)
                    logging.info(f"Сообщение отправлено пользователю {user_id}: {response_text}")
                except Exception as e:
                    logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

                await asyncio.sleep(1)

        await asyncio.sleep(600)

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

        await message.reply("Бот запущен. Отправьте команду /seturl <ссылка>, чтобы установить ссылку для мониторинга.")
        logging.info(f"Пользователь {user_id} добавлен в users.txt.")
    except Exception as e:
        await message.reply("Произошла ошибка при сохранении вашего ID. Пожалуйста, попробуйте позже.")
        logging.error(f"Ошибка записи ID пользователя {user_id} в файл: {e}")

# Обработчик команды /seturl
@dp.message_handler(commands=['seturl'])
async def set_url(message: types.Message):
    global user_urls

    user_id = message.chat.id
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.reply("Пожалуйста, укажите ссылку. Пример: /seturl <ссылка>")
        return

    user_url = args[1]
    user_urls[user_id] = user_url

    await message.reply("Ссылка установлена. Бот начнет мониторинг.")

    # Запускаем фоновую задачу для мониторинга
    driver = init_driver()
    asyncio.create_task(monitor_vinted_updates(user_id, user_url, driver))

if __name__ == '__main__':
    try:
        logging.info("Запуск бота...")
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logging.critical(f"Критическая ошибка запуска бота: {e}")
