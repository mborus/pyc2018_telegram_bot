#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Simple Bot to reply to Telegram messages.
This program is dedicated to the public domain under the CC0 license.
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import time
import os
import subprocess
import requests


import quick_parse_sessions

TOKEN_TELEGRAM = "insert api token here"

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

pyc = quick_parse_sessions.PyCamp()


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text("""Hallo. Ich bin dein PythonCamp Bot.
    
Ich kann Dir Fragen nach der Zeit und den Räumen beantworten.
    
Tippe 'zeit' oder 'raum'.
    
""")


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text(quick_parse_sessions.random_advice())


def echo(bot, update):
    """Echo the user message."""
    logger.debug(update.message.text)

    if 'time' in update.message.text.lower():
        return start_times(bot, update)
    if 'zeit' in update.message.text.lower():
        return start_times(bot, update)
    if 'room' in update.message.text.lower():
        return room(bot, update)
    if 'raum' in update.message.text.lower():
        return room(bot, update)

    update.message.reply_text('{}? Das habe ich nicht verstanden...'.format(update.message.text))



def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def room(bot, update):
    """Send a message when the command /start is issued."""

    keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in pyc.filter_rooms(all=True)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Bitte wählen:', reply_markup=reply_markup)


def start_times(bot, update):
    """Send a message when the command /start is issued."""

    keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in pyc.filter_session_times()]

    if not keyboard:
        update.message.reply_text('keine Startzeiten vorhanden')

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Bitte wählen:', reply_markup=reply_markup)


def return_time_result(timestring):

    _tmp = ['in {}: {}'.format(ev[1], ev[0]) for ev in pyc.filter_session_time(timestring)]
    if not _tmp:
        _tmp = ['bisher keine geplant.']
    return 'Sessions um {}\n{}'.format(timestring, '\n'.join(_tmp))


def return_room_result(room):
    _tmp = ['um {}: {}'.format(ev[0], ev[1]) for ev in pyc.filter_session_room(room)]
    if not _tmp:
        _tmp =  ['bisher keine geplant.']

    return 'Sessions in {}\n{}'.format(room, '\n'.join(_tmp))


def button(bot, update):
    query = update.callback_query

    if query.data in pyc.rooms:
        text = return_room_result(query.data)
    else:
        text = return_time_result(query.data)

    bot.edit_message_text(text=text,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)


def main():
    """Start the bot."""

    logger.debug('start bot')
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(TOKEN_TELEGRAM)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("hilfe", help))

    dp.add_handler(CommandHandler("room", room))
    dp.add_handler(CommandHandler("time", start_times))
    dp.add_handler(CommandHandler("raum", room))
    dp.add_handler(CommandHandler("zeit", start_times))

    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # on noncommand i.e message - echo the message on Telegram

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.

    i = 1
    while True:
        time.sleep(60)

        logger.debug('update')
        pyc.update()
        logger.debug(pyc.sessions)

    updater.idle()


if __name__ == '__main__':
    main()
