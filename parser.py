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

# Создаем объект бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Путь к драйверу Chrome
chrome_driver_path = r'/usr/bin/chromedriver'  # Обновите путь к драйверу на сервере

# Хранение ID обработанных объявлений
processed_ads = set()

# Переменные для работы
user_urls = {}  # Словарь для хранения ссылок для каждого пользователя
driver = None

# Функция для инициализации драйвера
def init_driver():
    global driver
    options = Options()
    options.add_argument("--headless")  # Включаем режим headless
    options.add_argument("--no-sandbox")  # Безопасный режим для сервера
    options.add_argument("--disable-dev-shm-usage")  # Уменьшение использования памяти
    options.binary_location = "/usr/bin/chromium-browser"

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

# Функция для загрузки страницы
def load_url(url):
    global driver
    driver.get(url)
    time.sleep(5)

    try:
        time.sleep(3)
        close_button = driver.find_element(By.CLASS_NAME, 'web_ui__Navigation__right')
        close_button.click()
        print("Кнопка закрытия нажата")
    except Exception as e:
        print(f"Ошибка при нажатии кнопок закрытия или принятия: {e}")

# Функция для получения первого товара
def get_first_vinted_item():
    global driver
    driver.refresh()
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

# Асинхронная функция для мониторинга обновлений на Vinted
async def monitor_vinted_updates(user_id):
    while True:
        user_url = user_urls.get(user_id)
        if not user_url:
            await bot.send_message(user_id, "Ссылка не задана. Используйте команду /seturl <ваша_ссылка>.")
            await asyncio.sleep(600)
            continue

        load_url(user_url)
        items = await asyncio.to_thread(get_first_vinted_item)

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
    global driver
    user_id = message.chat.id

    if driver is None:
        init_driver()

    await message.reply("Бот запущен. Используйте команду /seturl <ваша_ссылка>, чтобы задать ссылку для мониторинга.")
    asyncio.create_task(monitor_vinted_updates(user_id))

# Обработчик команды /seturl
@dp.message_handler(commands=['seturl'])
async def set_url(message: types.Message):
    user_id = message.chat.id
    url = message.get_args()

    if not url:
        await message.reply("Пожалуйста, укажите ссылку. Пример: /seturl <ваша_ссылка>")
        return

    user_urls[user_id] = url
    await message.reply(f"Ссылка установлена: {url}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
