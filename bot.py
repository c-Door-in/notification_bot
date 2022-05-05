import logging

import telegram


logger = logging.getLogger('log.bot')

def send_message(token, chat_id, text):
    logger.info(f'Sending message to id {chat_id}')
    bot = telegram.Bot(token=token)
    bot.send_message(text=text, chat_id=chat_id)
