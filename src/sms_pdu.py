import sys
import binascii
import io
import datetime
import pprint  # noqa
import logging

import gsm0338  # noqa


class PDU():
    LOGGING_FMT = '[%(asctime)s.%(msecs)-3d][%(levelname)8s] %(message)s'
    LOGGING_DATE_FMT = '%Y/%m/%d %H:%M:%S'

    def __init__(self, line=None, log_level=logging.INFO):
        """
        """
        self._logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(fmt=self.LOGGING_FMT, datefmt=self.LOGGING_DATE_FMT)
        handler.setFormatter(fmt)
        self._logger.addHandler(handler)
        self._logger.propagate = False  # 親ロガーに伝搬しない
        self.enable_logger(log_level)

        self.pdu = {}

        if line is not None:
            self.parse_pdu(line)

    def __del__(self,):
        """
        """
        pass

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

    @property
    def timestamp(self,) -> str:
        return self.convert_timestamp_from_bytes_to_str(self.pdu['tp_scts'])

    @property
    def from_number(self,) -> str:
        return self.convert_from_number_from_bytes_to_str(self.pdu['sender_number'])

    @property
    def message(self,) -> str:
        message = ''
        if self.pdu['tp_dcs'] == 0x00:  # 8-bit reference number
            message = self.convert_from_8bit_to_7bit(self.pdu['tp_ud']['ud']).decode('gsm03.38')
        elif self.pdu['tp_dcs'] == 0x08:  # 0x08: 16-bit reference number
            message = self.pdu['tp_ud']['ud'].decode('utf-16-be')
        else:
            raise Exception('Unimplemented DCS: {}'.format(hex(self.pdu['tp_dcs'])))
        return message

    @property
    def mms(self,) -> bool:
        return False if self.pdu['sms_type'] & 0b00000100 else True  # More Message to Send # 後続データの有無

    def parse_user_data_header(self, udh: bytearray) -> list:
        # [9.2.3.24.1 Concatenated Short Messages] https://www.arib.or.jp/english/html/overview/doc/STD-T63v9_20/5_Appendix/Rel9/23/23040-930.pdf
        # https://www.au.com/content/dam/au-com/okinawa_cellular/common/pdf/corporate/disclosure/setsuzoku_yakkan/gijutsu.pdf
        out = []
        tmp = dict(iei=None, iedl=None, ied=None)
        d = io.BytesIO(udh)

        while True:
            iei = d.read(1)
            if len(iei) == 0:
                break
            tmp['iei'] = iei[0]  # Information Element Identifier
            tmp['iedl'] = d.read(1)[0]  # Information Element Data Length
            tmp['ied'] = d.read(tmp['iedl'])  # Information Element Data
            # IED
            #     Octet1 8bit連結SM整理番号(FIXME: 2Byteある？)
            #     Octet2 最大SM番号
            #     Octet3 シーケンス番号
            out.append(tmp)
        return out

    def parse_user_data(self, ud: bytearray) -> dict:
        out = dict(udhl=None, udh=None, ud=None)
        d = io.BytesIO(ud)

        sms_type = self.pdu['sms_type']
        udhi = sms_type & 0b01000000  # User Data Header Indicate # UDHの有無

        if udhi:
            out['udhl'] = d.read(1)[0]
            out['udh'] = self.parse_user_data_header(d.read(out['udhl']))

        out['ud'] = d.read()
        return out

    def parse_pdu(self, line: str):
        # tp_pid
        # tp_dsc
        # tp_scts  (bytearray)
        # tp_udl   (int)
        # tp_ud    (dict)
        #     udhl (int)
        #     udh  (list)
        #     ud   (bytearray)

        data = binascii.unhexlify(line)
        d = io.BytesIO(data)

        # SMSC: ShotMessage ServiceCenter
        self.pdu['smsc_length'] = d.read(1)[0]
        if self.pdu['smsc_length'] > 0:
            self.pdu['type_of_address'] = d.read(1)[0]
            self.pdu['service_center_number'] = d.read(self.pdu['smsc_length']-1)  # NOTE: semioctet, With an "f" at the end.

        self.pdu['sms_type'] = d.read(1)[0]
        self.pdu['address_length'] = d.read(1)[0]
        self.pdu['type_of_address'] = d.read(1)[0]
        self.pdu['sender_number'] = d.read(int((self.pdu['address_length']+1)/2))  # NOTE: semioctet, With an "f" at the end.

        # TP: Transport Protocol
        self.pdu['tp_pid'] = d.read(1)[0]  # Protocol identifier
        self.pdu['tp_dcs'] = d.read(1)[0]  # Data coding scheme
        self.pdu['tp_scts'] = d.read(7)  # Timestamp # NOTE: semioctet
        self.pdu['tp_udl'] = d.read(1)[0]  # User data length
        self.pdu['tp_ud'] = self.parse_user_data(d.read(self.pdu['tp_udl']))  # User data

    def semioctet(self, x: bytearray) -> str:
        hex_str_list = list(binascii.hexlify(x).decode('utf-8'))
        out = ''
        while len(hex_str_list):
            out += hex_str_list.pop(1)
            out += hex_str_list.pop(0)
        return out

    def convert_timestamp_from_bytes_to_str(self, bs: bytearray) -> str:
        # [9.2.3.11 TP-Service-Center-Time-Stamp(TP-SCTS)] https://www.arib.or.jp/english/html/overview/doc/STD-T63v9_20/5_Appendix/Rel9/23/23040-930.pdf
        v = self.semioctet(bs)
        timestamp = datetime.datetime(2000 + int(v[:2]), int(v[2:4]), int(v[4:6]),
                                      int(v[6:8]), int(v[8:10]), int(v[10:12]))
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')  # + f'{v[12:14]}'

    def convert_from_number_from_bytes_to_str(self, bs: bytearray) -> str:
        return self.semioctet(bs).replace('f', '')

    def convert_from_8bit_to_7bit(self, bs: bytearray) -> bytearray:
        """Convert from 8bit to 7bit(GSM03.38)

        Args:
            bs (bytearray): 8bit user data

        Returns:
            bytearray: 7bit(GSM03.38)
        """
        # https://www.codeproject.com/Tips/470755/Encoding-Decoding-7-bit-User-Data-for-SMS-PDU-PDU
        out = bytearray()
        pc = 0  # previous carry
        pc_len = 0  # pc length
        i = 0
        count = 0
        while True:
            s = i % 8 + 1  # 1 ~ 8

            if s == 8:
                c = 0
                sept = 0
            else:
                octet = bs[count]
                c = octet >> (8 - s)
                sept = octet & (0xFF >> s)

                count += 1

            sept = (sept << pc_len) | pc
            out.append(sept)

            pc = c
            pc_len = s % 8

            i += 1

            if count >= len(bs):
                break
        return out


if __name__ == "__main__":
    """
    """
    message_list = [
        '0891180945123481F44012D04E2A15447C0E9FCD270008229072013503638B060804DCEB0301301030C930B330E2304B3089306E304A77E53089305B3011000D000A672C30E130FC30EB306F682A5F0F4F1A793E004E0054005430C930B330E2304B3089901A4FE16599712165993067914D4FE1305730663044307E30593002000D000A000D000A30C930B330E2304B3089306E91CD8981306A304A77E53089305B3084006430DD30A4',  # noqa
        '0891180945123481F44012D04E2A15447C0E9FCD270008229072013503638B060804DCEB030230F330C830923054522975283044305F3060304F305F3081306B306F521D671F8A2D5B9A304C5FC589813068306A308A307E30593002000D000A4EE54E0B306E00550052004C306E51855BB9306B5F933063306630C930B330E230B530FC30D330B9306E8A2D5B9A3092304A985830443044305F3057307E30593002FF08901A4FE16599',  # noqa
        '0891180945123481F44412D04E2A15447C0E9FCD2700082290720135036381060804DCEB030367096599FF09000D000A0068007400740070003A002F002F0073006500720076006900630065002E0073006D0074002E0064006F0063006F006D006F002E006E0065002E006A0070002F0073006900740065002F006D00610069006C002F007300720063002F00630063006E002E00680074006D006C000D000A',  # noqa
        '0891180945123451F4040B800000000000F00000229082110255631BE13A1D5D76D3D3E3303DFD7683C66F72591193CD6835DB0D'
    ]

    for m in message_list:
        pdu = PDU(m)
        pprint.pprint(pdu.pdu)
        # print(pdu.from_number)
        # print(pdu.message)
