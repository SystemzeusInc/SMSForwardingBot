import sys
import time
import configparser
import json
import datetime
import pprint  # noqa
from typing import List
import logging

import schedule
import jinja2
from slack_sdk import WebClient

from at import AT
from sms_pdu import PDU
import util


class SMSForwardingTask():
    LOGGING_FMT = '[%(asctime)s.%(msecs)-3d][%(levelname)8s] %(message)s'
    LOGGING_DATE_FMT = '%Y/%m/%d %H:%M:%S'

    def __init__(self, log_level: int = logging.INFO) -> None:
        """Initialize

        Args:
            log_level (int, optional): Level of logging. Defaults to logging.INFO.
        """
        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(fmt=self.LOGGING_FMT, datefmt=self.LOGGING_DATE_FMT)
        handler.setFormatter(fmt)
        self._logger.addHandler(handler)
        self._logger.propagate = False  # 親ロガーに伝搬しない
        self.enable_logger(log_level)

        config = configparser.ConfigParser()
        config.read('../config/config.ini')

        with open('../token.json', 'r') as f:
            token = json.load(f)

        self.client = WebClient(token=token['bot_token'])

        self.port = config['serial']['port']
        self.slack_channel = config['setting']['slack_channel']
        self.interval_seconds = int(config['setting']['polling_seconds'])

    def __del__(self,):
        """
        """
        pass

    def enable_logger(self, level: int = logging.INFO) -> None:
        """Enable logger. Set level.

        Args:
            level (int): Level of logging. Defaults to logging.INFO.
        """
        self._logger.setLevel(level)

    def disable_logger(self,) -> None:
        """Disable logger
        """
        self._logger.setLevel(logging.NOTSET)

    def decode_pdu_message(self, msg: str) -> List[PDU]:
        """Decode PDU message
        ATコマンドで取得したPDUをデコード

        [参]
        - http://www.gsm-modem.de/sms-pdu-mode.html
        - https://www.soumu.go.jp/main_content/000739753.pdf

        Args:
            msg (str): PDU message. ex) +CMGL: <index>,<stat>,[<alpha>],<length><CR><LF><pdu><CR><LF>

        Returns:
            List[PDU]: Decoded PDU list
        """
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

    def create_sms_list_from_pdu_list(self, pdu_list: List[PDU]) -> list[dict]:
        """Create SMS list from PDU list

        Args:
            pdu_list (List[PDU]): PDU list

        Returns:
            list[dict]: SMS list
        """
        sms_list = []

        mms_list = list(filter(lambda x: x.pdu['tp_ud']['udh'] is not None, pdu_list))
        not_mms_list = list(filter(lambda x: x.pdu['tp_ud']['udh'] is None, pdu_list))

        # IED
        #     Octet1-2 8bit連結SM整理番号
        #     Octet2   最大SM番号
        #     Octet3   シーケンス番号
        linking_number_list = list(set(list(map(lambda x: x.pdu['tp_ud']['udh'][0]['ied'][0:2], mms_list))))

        for linking_number in linking_number_list:
            linking_list = list(filter(lambda x: x.pdu['tp_ud']['udh'][0]['ied'][0:2] == linking_number, mms_list))
            sorted_list = sorted(linking_list, key=lambda x: x.pdu['tp_ud']['udh'][0]['ied'][-1])

            message = ''
            for s in sorted_list:
                message += s.message
            sms_list.append(dict(timestamp=s.timestamp, message=message, from_number=s.from_number))

        for m in not_mms_list:
            sms_list.append(dict(timestamp=m.timestamp, message=m.message, from_number=m.from_number))

        return sms_list

    def send_sms_to_slack(self,) -> None:
        """Send SMS to Slack
        SMSをATコマンドで取得からSlackに送信までの一連の動作
        """
        # SMS(PDU)取得
        at = AT(port=self.port)
        msg = at.get_sms_pdu(state=0)

        # PDUパース
        pdu_list = self.decode_pdu_message(msg)

        # SMSリスト作成
        sms_list = self.create_sms_list_from_pdu_list(pdu_list)

        # 除外する電話番号取得
        exclusion_number_list = util.get_exclusion_list()

        with open('../template/slack_message_template.txt', 'r') as f:
            template = jinja2.Template(f.read())

        for sms in sms_list:
            render_sms = template.render(from_number=sms['from_number'],
                                         message=sms['message'],
                                         timestamp=sms['timestamp'])

            # # Slackでカラーコードが表示されるのを防止 # FIXME: 暫定
            # render_sms = re.sub(r'#([0-9]{6})', r'# \1', render_sms)
            self._logger.debug(render_sms)

            # 受信したSMSを保存
            save_filename = '../data/receive_sms_{}.txt'.format(datetime.date.today().strftime('%Y%m%d'))
            with open(save_filename, 'a') as f:
                f.write(render_sms + '\n')

            if sms['from_number'] in exclusion_number_list:
                self._logger.debug('exclude sms message from {}'.format(sms['from_number']))
                continue

            # Slackに送信
            self.client.chat_postMessage(channel=self.slack_channel, text=render_sms)

    def start(self,) -> None:
        """Start SMS Forwarding Task
        """
        schedule.every(self.interval_seconds).seconds.do(self.send_sms_to_slack)

        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    """
    """
    sms_forwarding_task = SMSForwardingTask()
    sms_forwarding_task.enable_logger(logging.DEBUG)
    sms_forwarding_task.send_sms_to_slack()
