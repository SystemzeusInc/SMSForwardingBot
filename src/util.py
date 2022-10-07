import sys
import subprocess
import psutil
import logging
from typing import List

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


def get_raspberry_pi_info() -> dict:
    """Get Raspberry Pi info

    Returns:
        dict: Raspberry Pi info
    """
    info = {}

    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    mem_percent = mem.used / mem.total * 100

    info['cpu'] = f'{cpu_percent}%'
    info['mem'] = f'{mem_percent:.1f}%'

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


def get_exclusion_list() -> List[str]:
    """Get exclusion list

    Returns:
        List[str]: Exclusion list
    """
    with open('../config/exclude_number.txt', 'r') as f:
        data = f.read()
    data = data.strip().split('\n')
    data = sum(list(map(lambda x: x.split(','), data)), [])  # flatten
    return data


def add_exclusion_list(number: str) -> None:
    """Add exclusion list

    Args:
        number (str): Number to be excluded
    """
    with open('../config/exclude_number.txt', 'a') as f:
        f.write(str(number) + '\n')


def delete_exclusion_list(number: str) -> bool:
    """Delete exclusion list

    Args:
        number (str): Number to be removed from exclusion list

    Returns:
        bool: False if number does not exist in exclusion list
    """
    data = get_exclusion_list()
    new_data = [d for d in data if d != number]

    if number not in data:
        return False

    with open('../config/exclude_number.txt', 'w') as f:
        for d in new_data:
            f.write(str(d) + '\n')
    return True
