import sys
import time
import pprint  # noqa
import logging
import argparse
import json
import threading

import schedule
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import jinja2

from at import AT
from sms_pdu import PDU
import util

PROG = 'SMS Forwarding Bot'
__version__ = '0.1.0'

SLACK_CHANNEL = '#test_sms'  # 送信先のSlackのチャンネル
INTERVAL_SECONDS = 60  # ポーリングする間隔[s]
PORT = '/dev/ttyUSB1'  # モデムのポート

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

client = WebClient(token=BOT_TOKEN)
app = App(token=BOT_TOKEN)


def decode_pdu_message(msg: str) -> list:
    # +CMGL: <index>,<stat>,[<alpha>],<length><CR><LF><pdu><CR><LF>

    # http://www.gsm-modem.de/sms-pdu-mode.html
    # https://www.soumu.go.jp/main_content/000739753.pdf

    msg_list = msg.split('\n')

    cmgl_flag = False
    pi_list = []
    for line in msg_list:
        line = line.strip()

        if len(line) == 0:  # 空行除外
            continue

        if 'OK' in line:  # 終了
            break

        if '+CMGL:' in line:
            # cmgl_line = line.split(',')
            # pdu_length = int(cmgl_line[3], 16)
            cmgl_flag = True
        elif cmgl_flag:
            pdu = PDU(line)
            pi_list.append(pdu)

            cmgl_flag = False

    return pi_list


def create_sms_list_from_pdu(pdu_list: list) -> list:
    sms_list = []

    mms_list = list(filter(lambda x: x.pdu['tp_ud']['udh'] is not None, pdu_list))
    not_mms_list = list(filter(lambda x: x.pdu['tp_ud']['udh'] is None, pdu_list))

    # IED
    #     Octet1 8bit連結SM整理番号(FIXME: 2Byteある？)
    #     Octet2 最大SM番号
    #     Octet3 シーケンス番号
    linking_number_list = list(set(list(map(lambda x: x.pdu['tp_ud']['udh'][0]['ied'][0], mms_list))))

    for linking_number in linking_number_list:
        linking_list = list(filter(lambda x: x.pdu['tp_ud']['udh'][0]['ied'][0] == linking_number, mms_list))
        sorted_list = sorted(linking_list, key=lambda x: x.pdu['tp_ud']['udh'][0]['ied'][-1])

        message = ''
        for s in sorted_list:
            message += s.message
        sms_list.append(dict(timestamp=s.timestamp, message=message, from_number=s.from_number))

    for m in not_mms_list:
        sms_list.append(dict(timestamp=m.timestamp, message=m.message, from_number=m.from_number))

    return sms_list


def send_sms_to_slack() -> None:
    at = AT(port=PORT)
    msg = at.get_sms_pdu(state=0)

    pdu_list = decode_pdu_message(msg)
    sms_list = create_sms_list_from_pdu(pdu_list)

    # 除外する電話番号取得
    exclusion_number_list = util.get_exclusion_list()

    sms_template = '''<<<From {{from_number}} 
{{timestamp}}
{{message}}'''
    template = jinja2.Template(sms_template)

    for sms in sms_list:
        if sms['from_number'] in exclusion_number_list:
            continue
        render_sms = template.render(from_number=sms['from_number'],
                                     message=sms['message'],
                                     timestamp=sms['timestamp'])
        print(render_sms)
        client.chat_postMessage(channel=f'{SLACK_CHANNEL}', text=render_sms)  # Slackに送信


@app.command('/add_exclusion')
def add_exclusion_list_command(ack, say, command):
    number = command['text']

    util.add_exclusion_list(number)
    ack(f'除外リストに「{number}」を追加しました')


@app.command('/delete_exclusion')
def delete_exclusion_list_command(ack, say, command):
    number = command['text']

    message = ''
    if util.delete_exclusion_list(number):
        message = f'除外リストから「{number}」を削除しました'
    else:
        message = f'除外リストに「{number}」は存在しません'
    ack(message)


@app.command('/get_exclusion')
def get_exclusion_list_command(ack, say, command):
    data = util.get_exclusion_list()
    ack(str(data))


@app.command('/get_bot_info')
def get_bot_info(ack, say, command):
    raspi_info = util.get_raspberry_pi_info()

    message = f'''{PROG}
Ver {__version__}
Temp: {raspi_info['temp']}, Volt: {raspi_info['volt']}'''
    ack(message)


def transfer_sms():
    schedule.every(INTERVAL_SECONDS).seconds.do(send_sms_to_slack)

    while True:
        schedule.run_pending()
        time.sleep(1)


def actions_on_bot():
    handler = SocketModeHandler(app, APP_TOKEN)
    handler.start()


def main():
    """
    """
    logger.debug('Start...')

    thread1 = threading.Thread(target=transfer_sms)
    thread2 = threading.Thread(target=actions_on_bot)
    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()


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
