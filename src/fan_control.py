#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# InfluxDB に記録された外気温と室内気温に基づいて
# 換気扇を自動制御します．

import sys
import logging
import logging.handlers
import datetime
import pathlib
import time
import logging
import os

import influxdb_client

from config import load_config
import logger
import yamaha_usb_ctrl

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

# InfluxDB にアクセスしてセンサーデータを取得
def get_db_value(
    config,
    hostname,
    measure,
    param,
):
    token = os.environ.get("INFLUXDB_TOKEN", config["influxdb"]["token"])
    client = influxdb_client.InfluxDBClient(
        url=config["influxdb"]["url"],
        token=token,
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


logger.init("FAN auto control")

config = load_config()

while True:
    logging.info("Start.")

    temp_room = fetch_temp(config)

    if len(sys.argv) == 1:
        state = judge_fan_state(temp_room)
    else:
        state = sys.argv[1].lower() == "on"

    logging.info(
        "FAN: {} (temp_room: {:.2f})".format(
            "ON" if state else "OFF",
            temp_room if temp_room is not None else 0.0,
        )
    )
    fan_ctrl(config, state)

    logging.info("Finish.")
    pathlib.Path(config["liveness"]["file"]).touch()

    sleep_time = config["interval"] - datetime.datetime.now().second
    logging.info("sleep {sleep_time} sec...".format(sleep_time=sleep_time))
    time.sleep(sleep_time)
