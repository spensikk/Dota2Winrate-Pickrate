

from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import os
from dotenv import load_dotenv, dotenv_values

load_dotenv()



bot = telebot.TeleBot(token=os.getenv('token'))

ua = UserAgent()
headers = {'User-Agent': ua.random}

URLS = {
    'Mid lane': 'https://www.dotabuff.com/heroes?position=core-mid',
    'Safe lane': 'https://www.dotabuff.com/heroes?position=core-safe',
    'Off lane': 'https://www.dotabuff.com/heroes?position=core-off',
    'Hard support': 'https://www.dotabuff.com/heroes?position=support-safe',
    'Soft support': 'https://www.dotabuff.com/heroes?position=support-off',
    'All positions': 'https://www.dotabuff.com/heroes?show=facets&view=meta&mode=all-pick&date=7d'
}


@bot.message_handler(commands=['winrate', 'start'])
def start(message):
    buttons = telebot.types.ReplyKeyboardMarkup(True)
    keys_list = list(URLS.keys())
    buttons.row(*keys_list[:3])
    buttons.row(*keys_list[3:])
    bot.send_message(message.chat.id, 'Привет! Выбери позицию, чтобы узнать winrate героев.', reply_markup=buttons)


@bot.message_handler(content_types=['text'])
def user_input(message):
    if message.text in URLS:
        bot.send_chat_action(message.chat.id, 'typing')
        parse_heroes(URLS[message.text], message.chat.id)
    else:
        bot.send_message(message.chat.id, 'Неверная позиция, попробуй еще раз.')


def parse_heroes(url, chat_id, sort_by='winrate', edit=False):
    response = requests.get(url, headers=headers)
    bs = BeautifulSoup(response.text, 'html.parser')
    rows = bs.find('tbody').find_all('tr')

    sorted_rows = sorted(rows, key=lambda row: float(
        row.find_all('td')[2].find('span').get_text().strip('%')) if sort_by == 'winrate'
    else float(row.find_all('td')[4].find('span').get_text().strip('%')), reverse=True)

    text = ''
    for i, row in enumerate(sorted_rows[:10], 1):
        hero_name = row.find('div', class_='tw-flex tw-flex-col tw-gap-0').div.get_text()
        winrate = row.find_all('td')[2].find('span').get_text()
        aspect = row.find('div', class_='tw-text-xs tw-text-secondary').get_text()
        pickrate = row.find_all('td')[4].find('span').get_text()
        text += f"{i}. *{hero_name}* _({aspect})_ | Winrate: *{winrate}* | Pickrate: *{pickrate}*\n"

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton('Сортировать по Winrate', callback_data=f'{url}_winrate'),
               InlineKeyboardButton('Сортировать по Pickrate', callback_data=f'{url}_pickrate'))
    web_app = WebAppInfo(url=url)
    details_button = InlineKeyboardButton("Подробнее на Dotabuff", web_app=web_app)
    markup.row(details_button)

    if not edit:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

    return text, markup


@bot.callback_query_handler(func=lambda call: call.data.endswith('_winrate') or call.data.endswith('_pickrate'))
def callback_sort(call):
    sort_by = 'winrate' if call.data.endswith('_winrate') else 'pickrate'
    url = call.data.split('_')[0]
    text, markup = parse_heroes(url, call.message.chat.id, sort_by=sort_by, edit=True)
    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text,
                              reply_markup=markup, parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException:
        bot.answer_callback_query(call.id, 'Уже отсортировано.')


bot.infinity_polling()
