import sys
import subprocess
import logging

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


def get_raspberry_pi_info():
    info = {}
    cmd = ['vcgencmd', 'measure_temp']
    p = subprocess.run(cmd, encoding='utf-8',
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info['temp'] = p.stdout.strip().replace('temp=', '')

    cmd = ['vcgencmd', 'measure_volts']
    p = subprocess.run(cmd, encoding='utf-8',
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info['volt'] = p.stdout.strip().replace('volt=', '')

    logger.debug(info)
    return info


def get_exclusion_list() -> list:
    with open('../config/exclude_number.txt', 'r') as f:
        data = f.read()
    data = data.strip().split('\n')
    data = sum(list(map(lambda x: x.split(','), data)), [])  # flatten
    return data


def add_exclusion_list(number: str) -> None:
    with open('../config/exclude_number.txt', 'a') as f:
        f.write(str(number) + '\n')


def delete_exclusion_list(number: str) -> bool:
    data = get_exclusion_list()
    new_data = [d for d in data if d != number]

    if number not in data:
        return False

    with open('../config/exclude_number.txt', 'w') as f:
        for d in new_data:
            f.write(str(d) + '\n')
    return True
