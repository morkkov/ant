import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re

# Telegram bot token
API_TOKEN = '7759086372:AAEuRB_N-PbN_o-42WtfJT7oa9Cj_2ts3J8'  # Замените на ваш токен от BotFather
ADMIN_USERNAME = "@jdueje"  # Никнейм администратора в Telegram

# Создаем объект бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


chrome_driver_path = r'/usr/bin/chromedriver'

# Хранение ID обработанных объявлений
processed_ads = set()
user_urls = {}
driver = None

# Инициализация драйвера

def init_driver():
    global driver
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium-browser"

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

# Получение новых объявлений
def get_first_vinted_item(user_url):
    global driver

    driver.get(user_url)
    time.sleep(5)
    items = []

    try:
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

            except Exception as e:
                print(f"Ошибка при обработке первого объявления: {e}")
    except Exception as e:
        print(f"Ошибка при получении объявлений: {e}")

    return items

# Фоновый мониторинг объявлений
async def monitor_vinted_updates(user_id, user_url):
    while True:
        items = await asyncio.to_thread(get_first_vinted_item, user_url)

        if items:
            for item in items:
                title = item.get("title", "Без названия")
                price = item.get("price", "Цена не указана")
                link = item.get("url", "Нет ссылки")
                size = item.get('size', 'нет сайза')
                image_url = item.get('image_url', 'Нет изображения')

                response_text = f"Товар: {title}\nЦена: {price}\n{size}\n{image_url}\nСсылка: {link}"

                try:
                    await bot.send_message(chat_id=user_id, text=response_text)
                    print(f"Отправлено: {response_text}")
                except Exception as e:
                    print(f"Ошибка при отправке сообщения: {e}")

                await asyncio.sleep(1)

        await asyncio.sleep(600)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_monitoring(message: types.Message):
    global user_urls
    user_id = message.chat.id

    # Сохраняем ID нового пользователя в файл
    try:
        with open("users.txt", "a") as file:
            file.write(f"{user_id}\n")
    except Exception as e:
        print(f"Ошибка записи ID пользователя в файл: {e}")

    await message.reply("Бот запущен. Отправьте команду /seturl <ссылка>, чтобы установить ссылку для мониторинга.")

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
    asyncio.create_task(monitor_vinted_updates(user_id, user_url))

if __name__ == '__main__':
    init_driver()
    executor.start_polling(dp, skip_updates=True)
