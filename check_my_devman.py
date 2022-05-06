import json
import logging
from time import sleep, time

import requests
from requests.exceptions import ReadTimeout, ConnectionError
from environs import Env

from bot import send_message


logger = logging.getLogger('log')


def set_logger():
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('spam.log')
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    fmtstr = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    fmtdate = '%H:%M:%S'
    formater = logging.Formatter(fmtstr, fmtdate)
    fh.setFormatter(formater)
    ch.setFormatter(formater)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def fetch_user_reviews(url, token):
    payload = {
        'Authorization': f'Token {token}'
    }
    response = requests.get(url, headers=payload)
    response.raise_for_status()

    with open('user_reviews.json', 'w', encoding='utf8') as json_file:
        json.dump(response.json(), json_file, ensure_ascii=False)


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


def send_notification(token, chat_id, attempt_results):
    for result in attempt_results:
        is_negative = result['is_negative']
        lesson_title = result['lesson_title']
        lesson_url = result['lesson_url']
    result_text = (
        'К сожалению, в работе нашлись ошибки.'
    ) if is_negative else (
        'Преподавателю все понравилось, можно приступать к следующему уроку.'
    )
    text = (
        f'У вас проверили работу "{lesson_title}".\n' \
        f'{result_text}\n'\
        f'Ссылка на вашу работу:\n{lesson_url}'
    )
    send_message(token, chat_id, text)


def check_review(url, devman_token, timeout, tgbot_token, chat_id, timestamp = time()):
    while True:
        try:
            review_response = fetch_review_result(url, devman_token, timestamp, timeout)
        except ReadTimeout as e:
            logger.debug('Exception: %s' % str(e))
        except ConnectionError as e:
            logger.debug('Exception: %s' % str(e))
            sleep(timeout)
        else:
            logger.info('The status is "%s"' % review_response['status'])
            if not review_response['status'] == 'found':
                timestamp = review_response['last_attempt_timestamp']
                continue
            send_notification(
                tgbot_token,
                chat_id,
                review_response['new_attempts'],
            )
            timestamp = review_response['last_attempt_timestamp']
            


def main():
    logger = set_logger()
    logger.info('Start program')

    env = Env()
    env.read_env()
    devman_token = env.str("DEVMAN_TOKEN")
    tgbot_token=env.str('TGBOT_TOKEN')
    chat_id = env.str('TG_CHAT_ID')

    long_polling_url = 'https://dvmn.org/api/long_polling/'
    timeout=5
    logger.info(f'timeout is {timeout}')
    check_review(long_polling_url, devman_token, timeout, tgbot_token, chat_id)


if __name__ == '__main__':
    main()