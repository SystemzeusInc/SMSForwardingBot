import sys
import time
import logging

import serial


class AT():
    # https://www.diafaan.com/sms-tutorials/gsm-modem-tutorial/at-cmgl-pdu-mode/
    LOGGING_FMT = '[%(asctime)s.%(msecs)-3d][%(levelname)8s] %(message)s'
    LOGGING_DATE_FMT = '%Y/%m/%d %H:%M:%S'

    def __init__(self, port, timeout=3, log_level=logging.INFO):
        """
        """
        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(fmt=self.LOGGING_FMT, datefmt=self.LOGGING_DATE_FMT)
        handler.setFormatter(fmt)
        self._logger.addHandler(handler)
        self._logger.propagate = False  # 親ロガーに伝搬しない
        self.enable_logger(log_level)

        self.serial = serial.Serial(port,
                                    460800,
                                    timeout=timeout)

    def __del__(self,):
        """
        """
        self.serial.close()

    def enable_logger(self, level: int) -> None:
        """Enable logger. Set level.

        Args:
            level (int): Level of Logging
        """
        self._logger.setLevel(level)

    def disable_logger(self,) -> None:
        """Disable logger
        """
        self._logger.setLevel(logging.NOTSET)

    def read_response(self,) -> str:
        """Read response

        Returns:
            str: Response
        """
        response = ''
        while True:
            line = self.serial.readline().decode('utf-8')
            response += line

            if line.strip() == 'OK':
                break
            # elif line.strip() == 'ERROR':  # TODO:
            #     break
        return response

    def get_sms_text_message(self, state: str = 'REC UNREAD') -> str:
        """Get SMS text message

        Args:
            state (str: optional): {ALL | REC UNREAD | REC READ}. Defaults to 'REC UNREAD'.

        Returns:
            str: Text message (+CMGL: <index>,<stat>,<oa>,[<alpha>],[<scts>]<CR><LF><data><CR><LF>)
        """
        self.send_cmd('ATE1')
        resp = self.read_response()
        self._logger.debug(resp)

        time.sleep(0.5)

        self.send_cmd('AT+CMGF=1')  # 0: PDU Mode, 1: Text Mode
        resp = self.read_response()
        self._logger.debug(resp)

        time.sleep(0.5)

        self.send_cmd(f'AT+CMGL="{state}"')
        resp = self.read_response()
        self._logger.debug(resp)

        return resp

    def get_sms_pdu(self, state: int = 0) -> str:
        """Get SMS PDU

        Args:
            state (int, optional): {0(unread) | 1(read) | 4(all)}. Defaults to 0.

        Returns:
            str: PDU message (+CMGL: <index>,<stat>,[<alpha>],<length><CR><LF><pdu><CR><LF>)
        """
        self.send_cmd('ATE1')
        resp = self.read_response()
        self._logger.debug(resp)

        time.sleep(0.5)

        self.send_cmd('AT+CMGF=0')  # 0: PDU Mode, 1: Text Mode
        resp = self.read_response()
        self._logger.debug(resp)

        time.sleep(0.5)

        self.send_cmd(f'AT+CMGL={state}')
        resp = self.read_response()
        self._logger.debug(resp)

        return resp

    def send_cmd(self, cmd: str) -> None:
        """Send command

        Args:
            cmd (str): AT command
        """
        cmd = cmd + '\r'
        cmd = cmd.encode('utf-8')
        self.serial.write(cmd)
