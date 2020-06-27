#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# InfluxDB に記録された外気温と室内気温に基づいて
# 換気扇を自動制御します．

import json
import urllib.request
import subprocess
import sys
import time
import logging
import logging.handlers
import gzip
import datetime
import yaml
import os

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'lib'))

import yamaha_usb_ctrl

# YAMAH ルータの IP アドレス
YAMAHA_ROUTER = '192.168.2.1'
# 温度を取得する InfluxDB のアドレス
INFLUXDB_HOST = '192.168.2.20:8086'

class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, 'rb')
        f_out = gzip.open("%s.gz" % dest, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)

def get_logger():
    logger = logging.getLogger()
    log_handler = logging.handlers.RotatingFileHandler(
        '/dev/shm/fan_control.log',
        encoding='utf8', maxBytes=1*1024*1024, backupCount=10,
    )
    log_handler.formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(name)s :%(message)s',
        datefmt='%Y/%m/%d %H:%M:%S %Z'
    )
    log_handler.rotator = GZipRotator()

    logger.addHandler(log_handler)
    logger.setLevel(level=logging.INFO)

    return logger
        
def influxdb_get(db, host, name):
    url = 'http://' + INFLUXDB_HOST + '/query'

    params = {
        'db': 'sensor',
        'q': ('SELECT {} FROM "{}" WHERE "hostname" = \'{}\' AND time > now() - {} ' + 
              'ORDER by time desc LIMIT {}').format(name, db, host, '1h', '1')
    }
    data = urllib.parse.urlencode(params).encode("utf-8")

    try:
        with urllib.request.urlopen(url, data=data) as res:
            result = res.read().decode("utf-8")
            return json.loads(result)['results'][0]['series'][0]['values'][0][1]
    except:
        return None

def fan_ctrl(config, mode):
    yamaha_usb_ctrl.ctrl(config, YAMAHA_ROUTER, 'on' if state else 'off')

def judge_fan_state(temp_room):
    # 温度と時刻に基づいてファンの ON/OFF を決める

    now = datetime.datetime.now()

    # 夜は温度に関係なく止める
    if (now.hour < 8) or (now.hour > 20):
        return False

    # 室温不明ならとりあえず動かす
    if temp_room is None:
        return True

    # 室温が高温なら動かす
    if temp_room > 30:
        return True
    
    return False



logger = get_logger()

conf_file = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib', yamaha_usb_ctrl.DEFAULT_CONF_FILE))

config = yaml.load(open(conf_file, 'r'), Loader=yaml.BaseLoader)

temp_room = influxdb_get('sensor.raspberrypi', 'rasp-meter-3', 'temp')

if len(sys.argv) == 1:
    state = judge_fan_state(temp_room)
else:
    state = sys.argv[1].lower() == 'on'

fan_ctrl(config, state)

print('FAN is {}'.format('ON' if state else 'OFF'))

logger.info('FAN: {} (temp_room: {:.2f})'.format(
    'ON' if state else 'OFF',
    temp_room if temp_room is not None else 0.0,
))
