#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# InfluxDB に記録された外気温と室内気温に基づいて
# 換気扇を自動制御します．

import sys
import logging
import logging.handlers
import pathlib
import gzip
import datetime
import yaml
import time
import os

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

import yamaha_usb_ctrl

import influxdb_client

FLUX_QUERY = """
from(bucket: "{bucket}")
    |> range(start: -{period})
    |> filter(fn:(r) => r._measurement == "{measure}")
    |> filter(fn: (r) => r.hostname == "{hostname}")
    |> filter(fn: (r) => r["_field"] == "{param}")
    |> aggregateWindow(every: 3m, fn: mean, createEmpty: false)
    |> exponentialMovingAverage(n: 3)
    |> sort(columns: ["_time"], desc: true)
    |> limit(n: 1)
"""

CONFIG_PATH = "../config.yml"


def load_config():
    path = str(pathlib.Path(os.path.dirname(__file__), CONFIG_PATH))
    with open(path, "r") as file:
        return yaml.load(file, Loader=yaml.SafeLoader)


class GZipRotator:
    def namer(name):
        return name + ".gz"

    def rotator(source, dest):
        with open(source, "rb") as fs:
            with gzip.open(dest, "wb") as fd:
                fd.writelines(fs)
        os.remove(source)


def get_logger():
    logger = logging.getLogger()
    log_handler = logging.handlers.RotatingFileHandler(
        "/dev/shm/fan_control.log",
        encoding="utf8",
        maxBytes=1 * 1024 * 1024,
        backupCount=10,
    )
    log_handler.formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s :%(message)s",
        datefmt="%Y/%m/%d %H:%M:%S %Z",
    )
    log_handler.namer = GZipRotator.namer
    log_handler.rotator = GZipRotator.rotator

    logger.addHandler(log_handler)
    logger.setLevel(level=logging.INFO)

    return logger


# InfluxDB にアクセスしてセンサーデータを取得
def get_db_value(
    config,
    hostname,
    measure,
    param,
):
    client = influxdb_client.InfluxDBClient(
        url=config["influxdb"]["url"],
        token=config["influxdb"]["token"],
        org=config["influxdb"]["org"],
    )

    query_api = client.query_api()

    table_list = query_api.query(
        query=FLUX_QUERY.format(
            bucket=config["influxdb"]["bucket"],
            measure=measure,
            hostname=hostname,
            param=param,
            period="1h",
        )
    )

    return table_list[0].records[0].get_value()


def fetch_temp(config):
    try:
        return get_db_value(
            config,
            config["sensor"]["hostname"],
            config["sensor"]["measure"],
            config["sensor"]["param"],
        )
    except:
        return None


def fan_ctrl(config, mode):
    yamaha_usb_ctrl.ctrl(config, "on" if state else "off")


def judge_fan_state(temp_room):
    # 温度と時刻に基づいてファンの ON/OFF を決める

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=+9), "JST"))

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
config = load_config()

while True:
    temp_room = fetch_temp(config)

    if len(sys.argv) == 1:
        state = judge_fan_state(temp_room)
    else:
        state = sys.argv[1].lower() == "on"

        fan_ctrl(config, state)

    print("FAN is {}".format("ON" if state else "OFF"))
    sys.stdout.flush()

    logger.info(
        "FAN: {} (temp_room: {:.2f})".format(
            "ON" if state else "OFF",
            temp_room if temp_room is not None else 0.0,
        )
    )

    time.sleep(config["interval"])
