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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
splitter = SentenceSplitter()

def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Hello, to start just write me something (in English).")

def handle_message(update: Update, context: CallbackContext):
    wds = splitter.process(update.message.text)
    for wd in wds:
        persister.update_statistics(wd)
    recommendation = persister.get_recommended()
    context.bot.send_message(chat_id=update.effective_chat.id, text=recommendation)


def run_bot(TG_BOT_API_KEY):
    updater = Updater(token=TG_BOT_API_KEY)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(None, handle_message))
    updater.start_polling()


if __name__ == '__main__':
    load_dotenv('debug.env')

    DB_NAME = os.getenv('DB_NAME')
    DB_ADDRESS = os.getenv('DB_ADDRESS')
    TG_BOT_API_KEY = os.getenv('TG_BOT_API_KEY')



    client = pymongo.MongoClient(DB_ADDRESS)
    db = client[DB_NAME]
    persister = Persister(db)

    run_bot(TG_BOT_API_KEY)
