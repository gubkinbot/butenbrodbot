import telebot
import pandas as pd
from fuzzywuzzy import fuzz
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yaml
from os import path as os_path

config_path = os_path.abspath(os_path.join(os_path.dirname(__file__), 'config.yml'))
config = yaml.safe_load(open(config_path))

bot = telebot.TeleBot(config['TOKEN'])

ids = [2528316, -1001770890678, 263965948, 95700052, 543148778, 1221981431, 245304345, 57180126, 713287828]

data = pd.read_json('data_ru.json')
global_cats = data.columns
local_cats = data.index
summary = pd.DataFrame()
for global_cat in global_cats:
    for local_cat in local_cats:
        if len(str(data.loc[local_cat, global_cat])) > 3:
            current = pd.DataFrame.from_dict(data.loc[local_cat, global_cat])
            current['global'] = global_cat
            current['local'] = local_cat
            summary = summary.append(current)
summary.reset_index(inplace=True, drop=True)

def find(string):
    out = pd.DataFrame()
    for index in summary.index:
        current_string = summary.loc[index].title.lower()
        if string.lower() in current_string.split(' '):
            out = out.append(summary.loc[index])
    return out.drop_duplicates()

def find_maybe(string):
    out = pd.DataFrame()
    for index in summary.index:
        current_string = summary.loc[index].title.lower()
        if fuzz.WRatio(current_string, string) >= 90:
            out = out.append(summary.loc[index])
        for arr_str in current_string.split(' '):
            if len(arr_str) >= 3:
                if fuzz.WRatio(string, arr_str) >= 75:
                    out = out.append(summary.loc[index])
    return out.drop_duplicates()

def gen_markup(message_text, code):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(message_text, callback_data=code))
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: telebot.types.CallbackQuery):
    if call.message.chat.id in ids:
        if call.data == 'GO':
            bot.send_message(chat_id=-1001770890678, text=call.message.text, reply_markup=gen_markup('Уже были!', 'OK'), parse_mode='HTML')
            bot.answer_callback_query(call.id, "Готово!")
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Готово!")
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Вы не член команды")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, "Привет, детектив! Напиши мне, кого или что ты ищешь!")

@bot.message_handler(commands=['office'])
def send_welcome(message):
    if message.chat.id in ids:
        bot.reply_to(message, "Список адресов, куда надо поехать")
    else:
        bot.reply_to(message, "Действие доступно только для членов команды")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if message.text.find('-') > 0:
        address = summary[summary.address == message.text]
        address_message = f'''<b>Имя: {address.iloc[0]['title']}
Адрес: <code>{address.iloc[0]['address']}</code></b>
Категория: {address.iloc[0]['global']}, {address.iloc[0]['local']}'''
        bot.reply_to(message, address_message, parse_mode='HTML', reply_markup=gen_markup('Поехали!', 'GO'))
        
    else:
        results = find(message.text)
        results_maybe = find_maybe(message.text)
        summary_result_string = ''
        summary_result_maybe_string = ''
        for result in results.index:
            result_string = f'''Имя: {results.loc[result]['title']}
Адрес: <code>{results.loc[result]['address']}</code>
Категория: {results.loc[result]['global']}, {results.loc[result]['local']}

'''
            summary_result_string = summary_result_string + result_string
        
        for result_maybe in results_maybe.drop(results.index).index:
            result_maybe_string = f'''Имя: {results_maybe.loc[result_maybe]['title']}
Адрес: <code>{results_maybe.loc[result_maybe]['address']}</code>
Категория: {results_maybe.loc[result_maybe]['global']}, {results_maybe.loc[result_maybe]['local']}

'''
            summary_result_maybe_string = summary_result_maybe_string + result_maybe_string

        if len(summary_result_string) == 0:
            bot.reply_to(message, 'Не смог найти прямого совпадения')
        else:
            bot.reply_to(message, f'''<b>Прямое совпадение:</b>

''' + summary_result_string, parse_mode='HTML')

        if len(summary_result_maybe_string) == 0:
            bot.reply_to(message, 'А больше посоветовать нечего...')
        else:
            bot.reply_to(message, f'''<b>Похожие результаты:</b>

''' + summary_result_maybe_string, parse_mode='HTML')

bot.infinity_polling()
