import logging
import xml.etree.ElementTree as ET
from os import environ

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

RSS_URL = environ.get('RSS_URL')
TELEGRAM_TOKEN = environ.get('TELEGRAM_TOKEN')
CHAT_ID = environ.get('CHAT_ID')
CHECK_TIMEOUT = environ.get('CHECK_TIMEOUT')

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

latest_item_id = None


async def callback_auto_message(context: ContextTypes.DEFAULT_TYPE):
    global latest_item_id

    job = context.job

    response = requests.get(RSS_URL)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items = root.findall('.//item')

    new_items = []

    for item in items:
        item_id = item.find('guid').text
        if item_id == latest_item_id:
            break
        new_items.append(item)

    if new_items:
        latest_item_id = new_items[0].find('guid').text
        for item in reversed(new_items):
            title = item.find('title').text
            link = item.find('link').text
            enclosure_url = item.find('enclosure').attrib['url']

            message = f"{title}\n{link}\n{enclosure_url}"
            await context.bot.send_message(job.chat_id, text=message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    context.job_queue.run_repeating(callback_auto_message, int(CHECK_TIMEOUT), name=str(chat_id), chat_id=chat_id)
    await context.bot.send_message(chat_id=chat_id, text=f'Start automatic check rss feed. Request every {CHECK_TIMEOUT} sec.')


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Checker successfully cancelled!" if job_removed else "You have no active checkers."
    await update.message.reply_text(text)


def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
