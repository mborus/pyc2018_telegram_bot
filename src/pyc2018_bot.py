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

raum - Liste der Räume
zeit - Startzeiten
jetzt - aktuelle Sessions
gleich - kommende Sessions

"""
import time
import os
import subprocess
import requests

from settings import BOT_TOKEN, BOTNAME, SESSION_URL

import quick_parse_sessions

TOKEN_TELEGRAM = BOT_TOKEN  #  "insert api token here"

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

mybots = {}
pyc = quick_parse_sessions.PyCamp()


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        """Hallo. Ich bin dein PythonCamp Bot.
    
Ich kann Dir Fragen nach der Zeit und den Räumen beantworten.
    
Tippe 'jetzt, 'gleich', 'zeit' oder 'raum' oder nutze die Befehlsfunktion von Telegram.
    
"""
    )


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text(quick_parse_sessions.random_advice())


def echo(bot, update):
    """Echo the user message."""
    logger.debug(update.message.text)
    message = update.message.text.lower()

    # messages zeit, time
    if any(
        [
            message.startswith("t"),
            message.startswith("z"),
            "time" in message,
            "zeit" in message,
        ]
    ):
        return start_times(bot, update)

    # messages room, raum
    if any([message.startswith("r"), "room" in message, "raum" in message]):
        return room(bot, update)

    # messages current, jetzt
    if any([message.startswith("j"),
            message.startswith("no"),
            "jetzt" in message, "now" in message]):
        return sessions_now(bot, update)

    # messages next, gleich
    if any([message.startswith("g"),
            message.startswith("n"),
            'gleich' in message, "next" in message]):
        return sessions_next(bot, update)

    update.message.reply_text(
        "{}? Das habe ich nicht verstanden...".format(update.message.text)
    )

    mybots[update.message.chat_id] = bot


def alarm(bot, job):
    """Send the alarm message."""
    bot.send_message(job.context, text="Beep!")


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def room(bot, update):
    """Send a message when the command /start is issued."""
    if pyc.rooms:
        keyboard = [
            [InlineKeyboardButton(opt, callback_data=opt)]
            for opt in pyc.rooms
            if not any(
                ["morgen" in (opt or "").lower(), "ersatz" in (opt or "").lower()]
            )
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Bitte wählen:", reply_markup=reply_markup)


def start_times(bot, update):
    """Send a message when the command /start is issued."""

    if pyc.filter_session_times():
        keyboard = [
            [InlineKeyboardButton(opt, callback_data=opt)]
            for opt in pyc.filter_session_times()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Bitte wählen:", reply_markup=reply_markup)


def return_time_result(timestring):

    _tmp = [
        "in {}: {}".format(ev[1], ev[0]) for ev in pyc.filter_session_time(timestring)
    ]
    if not _tmp:
        _tmp = ["bisher keine geplant."]
    return "Sessions um {}\n{}".format(timestring, "\n".join(_tmp))


def return_room_result(room):
    _tmp = ["um {}: {}".format(ev[0], ev[1]) for ev in pyc.filter_session_room(room)]
    if not _tmp:
        _tmp = ["bisher keine geplant."]

    result = [ "Sessions in {}".format(room) ]
    creds = pyc.access_creds.get(room.upper())
    if creds:
        result.append("Url: {}".format(creds.get('url')))
        result.append("Code: {}".format(creds.get('access_code')))
        result.append("")
    result.extend(_tmp)

    return "\n".join(result)


def button(bot, update):
    query = update.callback_query

    if query.data in pyc.rooms:
        text = return_room_result(query.data)
    else:
        text = return_time_result(query.data)

    bot.edit_message_text(
        text=text, chat_id=query.message.chat_id, message_id=query.message.message_id
    )


def sessions_now(bot, update):
    timestring, _, current = pyc.get_now_and_next()
    update.message.reply_text(return_time_result(timestring or current))


def sessions_next(bot, update):
    _, timestring, current = pyc.get_now_and_next()
    update.message.reply_text(return_time_result(timestring or current))


def main():
    """Start the bot."""

    logger.debug("start bot")
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

    dp.add_handler(CommandHandler("now", sessions_now))
    dp.add_handler(CommandHandler("jetzt", sessions_now))
    dp.add_handler(CommandHandler("next", sessions_next))
    dp.add_handler(CommandHandler("gleich", sessions_next))

    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.

    i = 1
    while True:

        logger.debug("update")
        pyc.update()
        logger.debug(pyc.sessions)
        time.sleep(60)

        continue

        # kein beep
        for id, bot in mybots.items():
            i += 1
            bot.send_message(id, text="Beep! " + str(i))

    updater.idle()


if __name__ == "__main__":
    main()
