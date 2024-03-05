import os
import sys
import pprint  # noqa
import logging
import argparse
import json
import threading

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from forwarding_sms import SMSForwardingTask
from exclusion_list import add_exclusion_list, delete_exclusion_list, get_exclusion_list
from common.util import get_raspberry_pi_info

PROG = 'SMS Forwarding Bot'
__version__ = '1.0.0'


# トークン
with open('../token.json', 'r') as f:
    token = json.load(f)
BOT_TOKEN = token['bot_token']
APP_TOKEN = token['app_token']

LOGGING_FMT = '[%(asctime)s.%(msecs)-3d][%(levelname)8s] %(message)s'
LOGGING_DATE_FMT = '%Y/%m/%d %H:%M:%S'
# logging.basicConfig(level=logging.INFO, format=LOGGING_FMT, datefmt=LOGGING_DATE_FMT)

log_level = logging.INFO
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter(fmt=LOGGING_FMT, datefmt=LOGGING_DATE_FMT)
handler.setFormatter(fmt)
logger.addHandler(handler)
logger.propagate = False  # 親ロガーに伝搬しない

app = App(token=BOT_TOKEN)


@app.command('/add_exclusion')
def add_exclusion_list_command(ack, say, command, logger):
    number = command['text']

    add_exclusion_list(number)
    message = f'除外リストに「{number}」を追加しました'
    logger.debug(message)
    say(message)
    ack()


@app.command('/delete_exclusion')
def delete_exclusion_list_command(ack, say, command, logger):
    number = command['text']

    message = ''
    if delete_exclusion_list(number):
        message = f'除外リストから「{number}」を削除しました'
        logger.debug(message)
        say(message)
        ack()
    else:
        message = f'除外リストに「{number}」は存在しません'
        logger.debug(message)
        ack(message)


@app.command('/get_exclusion')
def get_exclusion_list_command(ack, say, command, logger):
    data = get_exclusion_list()
    message = '除外リスト: ' + str(data)
    logger.debug(message)
    ack(message)


@app.command('/get_bot_info')
def get_bot_info(ack, say, command, logger):
    raspi_info = get_raspberry_pi_info()

    message = f'''{PROG}  ver {__version__}

CPU: {raspi_info['cpu']}, Mem: {raspi_info['mem']}, Dsk: {raspi_info['dsk']}
Temp: {raspi_info['temp']}, Volt: {raspi_info['volt']}'''
    logger.debug(message)
    ack(message)


def command_task():
    handler = SocketModeHandler(app, APP_TOKEN)
    handler.start()


def main():
    """
    """
    logger.debug('Start...')

    try:
        if not os.path.isfile('../config/exclude_number.txt'):
            logger.info('make ../config/exclude_number.txt')
            with open('../config/exclude_number.txt', 'w') as f:
                f.write('')

        sms_fowarding_task = SMSForwardingTask(log_level=log_level)

        thread1 = threading.Thread(target=sms_fowarding_task.start)
        thread2 = threading.Thread(target=command_task)
        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

    except Exception as e:  # noqa
        logger.error(e)
    finally:
        pass


if __name__ == "__main__":
    """
    """
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--log-level', dest='log_level', choices=['debug', 'info', 'warn', 'error', 'critical'], default='info',
                        help='Set log level.')
    parser.add_argument('--version', action='version', version=f'{__version__}')
    args = parser.parse_args()

    if args.log_level == 'debug':
        log_level = logging.DEBUG
    elif args.log_level == 'info':
        log_level = logging.INFO
    elif args.log_level == 'warn':
        log_level = logging.WARN
    elif args.log_level == 'error':
        log_level = logging.ERROR
    else:
        log_level = logging.CRITICAL
    logger.setLevel(level=log_level)

    main()
