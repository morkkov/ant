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
chrome_driver_path = r'/usr/bin/chromedriver'
  # Обновите путь к драйверу на сервере

# Хранение ID обработанных объявлений
processed_ads = set()
driver = None
#1

def init_driver():
    global driver
    options = Options()
    options.add_argument("--headless")  # Включаем режим headless
    options.add_argument("--no-sandbox")  # Безопасный режим для сервера
    options.add_argument("--disable-dev-shm-usage")  # Уменьшение использования памяти
    options.binary_location = "/usr/bin/chromium-browser"

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(
        'https://www.vinted.pl/catalog?time=1733396236&catalog_from=0&brand_ids[]=449710&brand_ids[]=60712&brand_ids[]=1043&brand_ids[]=75090&brand_ids[]=235040&brand_ids[]=6501593&brand_ids[]=7164596&brand_ids[]=161&brand_ids[]=5821136&brand_ids[]=1482986&brand_ids[]=3799&brand_ids[]=4565&brand_ids[]=13197&brand_ids[]=15457&brand_ids[]=11521&brand_ids[]=424544&brand_ids[]=5969695&brand_ids[]=379819&brand_ids[]=7386290&brand_ids[]=10&brand_ids[]=3573&brand_ids[]=47829&brand_ids[]=17991&brand_ids[]=1153&brand_ids[]=123118&brand_ids[]=579801&page=1&order=newest_first')

    # Ожидание загрузки страницы
    time.sleep(5)

    # Пытаемся закрыть всплывающее окно и согласиться с куки
    try:
        time.sleep(3)
        # Кнопка закрытия
        close_button = driver.find_element(By.CLASS_NAME, 'web_ui__Navigation__right')
        close_button.click()
        print("Кнопка закрытия нажата")
    except Exception as e:
        print(f"Ошибка при нажатии кнопок закрытия или принятия: {e}")


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
                size_info = link_element.get_attribute("title")  # Получаем title элемента


                ad_parent = ad.find_element(By.CLASS_NAME, 'web_ui__Image__ratio')

# Ищем тег img внутри div
                img_tag = ad_parent.find_element(By.CLASS_NAME, 'web_ui__Image__content')

# Получаем URL изображения из атрибута src
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


async def monitor_vinted_updates():
    while True:
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
                    await bot.send_message(chat_id=USER_CHAT_ID, text=response_text)
                    print(f"Отправлено: {response_text}")
                except Exception as e:
                    print(f"Ошибка при отправке сообщения: {e}")

                await asyncio.sleep(1)

        await asyncio.sleep(600)
#1

@dp.message_handler(commands=['start'])
async def start_monitoring(message: types.Message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id

    init_driver()

    await message.reply("Бот запущен и будет отправлять обновления сразу, как только появится новый товар.")
    asyncio.create_task(monitor_vinted_updates())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)