"""Various."""
import subprocess
import psutil

def get_raspberry_pi_info() -> dict:
    """Get Raspberry Pi info.

    Returns:
        dict: Raspberry Pi info
    """
    info = {}

    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    mem_percent = mem.used / mem.total * 100
    dsk_percent = psutil.disk_usage('/').percent

    info['cpu'] = f'{cpu_percent}%'
    info['mem'] = f'{mem_percent:.1f}%'
    info['dsk'] = f'{dsk_percent:.1f}%'

    cmd = ['vcgencmd', 'measure_temp']
    p = subprocess.run(cmd, encoding='utf-8',
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info['temp'] = p.stdout.strip().replace('temp=', '')

    cmd = ['vcgencmd', 'measure_volts']
    p = subprocess.run(cmd, encoding='utf-8',
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info['volt'] = p.stdout.strip().replace('volt=', '')

    return info
