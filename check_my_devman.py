import logging
from logging.handlers import RotatingFileHandler
from textwrap import dedent
from time import sleep, time

import requests
import telegram
from requests.exceptions import ReadTimeout, ConnectionError
from environs import Env


logger = logging.getLogger('log')


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def fetch_review_result(url, token, timestamp, timeout):
    logger.debug(f'timestamp = {timestamp}')
    headers_payload = {'Authorization': f'Token {token}'}
    params_payload = {'timestamp': timestamp}
    response = requests.get(url,
                            headers=headers_payload,
                            params=params_payload,
                            timeout=timeout)
    response.raise_for_status()
    return response.json()


def send_notification(tg_bot, tg_chat_id, attempt_results):
    for result in attempt_results:
        is_negative = result['is_negative']
        lesson_title = result['lesson_title']
        lesson_url = result['lesson_url']
        result_text = (
            'К сожалению, в работе нашлись ошибки.'
        ) if is_negative else (
            'Преподавателю все понравилось, можно приступать к следующему уроку.'
        )
        text = (f'''\
            У вас проверили работу "{lesson_title}".
            {result_text}
            Ссылка на вашу работу:
            {lesson_url}
        ''')
        logger.debug(f'Sending message to id {tg_chat_id}')
        tg_bot.send_message(text=dedent(text), chat_id=tg_chat_id)


def main():
    logger.setLevel(logging.DEBUG)
    fh = RotatingFileHandler('spam.log', maxBytes=200, backupCount=2)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    fmtstr = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    fmtdate = '%H:%M:%S'
    formater = logging.Formatter(fmtstr, fmtdate)
    fh.setFormatter(formater)
    ch.setFormatter(formater)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.warning('Start program')

    env = Env()
    env.read_env()
    devman_token = env.str("DEVMAN_TOKEN")
    tg_chat_id = env.str('TG_CHAT_ID')
    tg_bot = telegram.Bot(token=env.str('TGBOT_TOKEN'))
    tg_logs_handler = TelegramLogsHandler(tg_bot, tg_chat_id)
    tg_logs_handler.setLevel(logging.WARNING)
    logger.addHandler(tg_logs_handler)

    timeout=env.int('REQUEST_TIMEOUT', None)
    logger.info(f'timeout is {timeout}')

    long_polling_url = 'https://dvmn.org/api/long_polling/'
    
    timestamp = time()
    logger.warning('Начало работы')
    while True:
        try:
            review_response = fetch_review_result(long_polling_url,
                                                  devman_token,
                                                  timestamp,
                                                  timeout)
        except ReadTimeout as err:
            logger.debug(err)
        except ConnectionError as err:
            logger.info(err)
            sleep(5)
        except Exception:
            logger.exception('Непредвиденная ошибка. Новая попытка через 60 секунд')
            sleep(60)
        else:
            status = review_response['status']
            logger.debug(f'The status is "{status}"')
            if not status == 'found':
                timestamp = review_response['timestamp_to_request']
                continue
            send_notification(
                tg_bot,
                tg_chat_id,
                review_response['new_attempts'],
            )
            timestamp = review_response['last_attempt_timestamp']


if __name__ == '__main__':
    main()