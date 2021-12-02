import logging
import pymongo
import os
from datetime import datetime

from persistence import Persister
from text_processing import SentenceSplitter

# Enable logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler

from word_list_setup import do_word_list_setup_internet

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
splitter = SentenceSplitter()

def send_recommendation(context, update):
    persister = persisters.get(update.message.from_user['id'])
    recommendation = persister.get_recommended()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Current recommended word is "{recommendation}"')

def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Initializing (it can take a minute)...")
    persister = persisters.get(update.message.from_user['id'])
    do_word_list_setup_internet(persister)

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Hello, to start just write me something (in English).")

def toggle_ignore(update: Update, context: CallbackContext):
    persister = persisters.get(update.message.from_user['id'])
    if len(context.args) > 0:
        lemma = context.args[0].lower().strip()
    else:
        lemma = persister.last_recommended
    res = persister.toggle_ignore(lemma)
    if res is None:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Could not find lemma {lemma}!')
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Changed "{lemma}" ignored state to "{res}"')
    send_recommendation(context, update)


def handle_message(update: Update, context: CallbackContext):
    persister = persisters.get(update.message.from_user['id'])
    persister.save_input(update.message.text)
    wds = splitter.process(update.message.text)
    for wd in wds:
        persister.update_statistics(wd)
    send_recommendation(context, update)

def setup_words(update, context):
    persister = persisters.get(update.message.from_user['id'])
    do_word_list_setup_internet(persister)
    send_recommendation(context, update)

def update_difficulty(update, context):
    persister = persisters.get(update.message.from_user['id'])
    try:
        difficulty = int(context.args[0])
    except:
        difficulty = persister.settings.start_skip
    persister.update_settings(start_skip=difficulty)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'Difficulty set to "{difficulty}"')
    send_recommendation(context, update)


def run_bot(TG_BOT_API_KEY):
    updater = Updater(token=TG_BOT_API_KEY)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('ignore', toggle_ignore))
    dispatcher.add_handler(CommandHandler('setup', setup_words))
    dispatcher.add_handler(CommandHandler('difficulty', update_difficulty))
    dispatcher.add_handler(MessageHandler(None, handle_message))
    updater.start_polling()

class PersisterCache:
    def __init__(self):
        self.persisters = {}

    def get(self, user_id):
        res = self.persisters.get(user_id, None)
        if res is None:
            res = Persister(db, user_id, START_SKIP)
            self.persisters[user_id] = res
        return res

if __name__ == '__main__':
    load_dotenv('debug.env')

    DB_NAME = os.getenv('DB_NAME')
    DB_ADDRESS = os.getenv('DB_ADDRESS')
    TG_BOT_API_KEY = os.getenv('TG_BOT_API_KEY')
    START_SKIP = int(os.getenv('START_SKIP', 500))



    client = pymongo.MongoClient(DB_ADDRESS)
    db = client[DB_NAME]
    persisters = PersisterCache()

    run_bot(TG_BOT_API_KEY)
