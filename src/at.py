import sys
import time
import logging

import serial

from common.log import Logger


class AT():
    def __init__(self, port: str, baudrate: int = 460800, timeout: int = 3, log_level: int = logging.INFO) -> None:
        """Initialize

        Args:
            port (str): Serial port
            baudrate (int, optional): Baudrate. Defaults to 460800.
            timeout (int, optional): pyserial timeout. Defaults to 3.
            log_level (int, optional): Level of logging. Defaults to logging.INFO.
        """
        self._logger = Logger(name=__name__, level=log_level)

        self.serial = serial.Serial(port,
                                    baudrate,
                                    timeout=timeout)

        self.send_cmd('ATE0')
        resp = self.read_response()
        self._logger.debug(resp)

    def __del__(self,):
        """Deinitialize
        """
        self.serial.close()

    def read_response(self,) -> str:
        """Read  AT response

        Returns:
            str: AT Response
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

        [参]
        - [4.1 List Messages +CMGL] https://www.arib.or.jp/english/html/overview/doc/STD-T63v9_10/5_Appendix/Rel10/27/27005-a00.pdf

        Args:
            state (int, optional): {0(unread) | 1(read) | 4(all)}. Defaults to 0.

        Returns:
            str: PDU message (+CMGL: <index>,<stat>,[<alpha>],<length><CR><LF><pdu><CR><LF>)
        """
        self.send_cmd('AT+CMGF=0')  # 0: PDU Mode, 1: Text Mode
        resp = self.read_response()
        self._logger.debug(resp)

        time.sleep(0.5)

        self.send_cmd(f'AT+CMGL={state}')
        resp = self.read_response()
        self._logger.debug(resp)

        return resp

    def delete_message(self, index: int = None, delflag: int = 1):
        """Delete message from message storage

        [参]
        - [3.5.4 Delete MEssage +CMGD] https://www.arib.or.jp/english/html/overview/doc/STD-T63v9_10/5_Appendix/Rel10/27/27005-a00.pdf

        Args:
            index (int, optional): index. Defaults to None.
            delflag (int, optional): {0 | 1 | 2 | 3 | 4}. Defaults to 1.
        """
        if index is None:
            index = 1
        self.send_cmd(f'AT+CMGD={index},{delflag}')
        resp = self.read_response()
        self._logger.debug(resp)

    def check_message_storage(self,):
        """Check message storage

        [参]
        - [3.2.2 Preferred Message Storage +CPMS] https://www.arib.or.jp/english/html/overview/doc/STD-T63v9_10/5_Appendix/Rel10/27/27005-a00.pdf
        """
        self.send_cmd('AT+CPMS="SM"')
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


if __name__ == "__main__":
    """
    """
    port = '/dev/ttyUSB1'
    at = AT(port=port)
    msg = at.get_sms_pdu(4)
    print(msg)
