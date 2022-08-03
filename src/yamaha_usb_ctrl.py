#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage: yamaha_usb_ctrl.py [-h] [-c CONF] MODE

YAMAHA ルータにログインして USB の ON/OFF を制御します．

Arguments:
  MODE              { ON | OFF }

Options:
  -c CONF           ログイン情報を記載した YAML ファイル
                    指定しなかった場合，カレントディレクトリの yamaha_config.yml
                    を使用します．

CONF で指定するファイルには，次の形式でログインするための
ユーザ名とパスワードを記載しておきます．

PASS: 「パスワード」
ADMIN: 「管理者パスワード」
"""

from docopt import docopt

import telnetlib
import sys
import logging

from config import load_config
import logger

TIMEOUT = 2


def print_progress(message, is_show=False):
    if is_show:
        print(message, end="")


def ctrl(config, mode, show_progress=False):
    pass_user = config["router"]["pass"]["user"]
    if config["router"]["pass"]["user"] is None:
        pass_user = ""
    pass_admin = config["router"]["pass"]["admin"]
    if config["router"]["pass"]["admin"] is None:
        pass_admin = ""

    logging.info("Login start.")

    tel = telnetlib.Telnet(config["router"]["addr"])
    tel.read_until(b"Password:")
    tel.write((pass_user + "\n").encode("utf-8"))
    tel.read_until(b"> ")

    logging.info("Login successful.")
    logging.info("Enable administrator.")

    tel.write(b"admin\n")
    tel.read_until(b"Password:")
    tel.write((pass_admin + "\n").encode("utf-8"))
    tel.read_until(b"# ")

    logging.info("Enable administrator OK.")
    logging.info("Set USB {mode}".format(mode=mode))

    tel.write(("usbhost use {mode}\n".format(mode=mode)).encode("utf-8"))
    res = tel.read_until(b"# ", TIMEOUT).decode("utf-8").split("\r\n")
    res.pop(0)
    res.pop(-1)

    error = "\n".join(res)

    if error != "":
        raise RuntimeError(error)


if __name__ == "__main__":
    logger.init("YAMAHA Router USB control")

    opt = docopt(__doc__)

    if opt.get("-c"):
        config = load_config(opt.get("CONF"))
    else:
        config = load_config()

    try:
        ctrl(config, opt.get("MODE").lower(), True)
    except RuntimeError as e:
        logging.error(e.args[0])
        sys.exit(-1)
