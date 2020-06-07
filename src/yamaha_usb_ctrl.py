#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Usage: yamaha_usb_ctrl.py [-h] [-c CONF] ADDR MODE

YAMAHA ルータにログインして USB の ON/OFF を制御します．

Arguments:
  ADDR              YAMAHA ルータアドレス
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
import yaml
import sys
import os

DEFAULT_CONF_FILE = 'yamaha_config.yml'
TIMEOUT           = 2

def print_progress(message, is_show=False):
    if is_show:
        print(message, end='')

def yamaha_usb_ctrl(config, addr, mode, show_progress=False):
    print_progress('Login        ... ', show_progress)

    tel = telnetlib.Telnet(addr)
    tel.read_until(b'Password:')
    tel.write((config['pass'] + '\n').encode('utf-8'))
    tel.read_until(b'> ')

    print_progress('OK\n', show_progress)

    print_progress('Enable admin ... ', show_progress)

    tel.write(b'admin\n')
    tel.read_until(b'Password:')
    tel.write((config['admin'] + '\n').encode('utf-8'))
    tel.read_until(b'# ')

    print_progress('OK\n', show_progress)

    tel.write(('usbhost use %s\n' % (mode)).encode('utf-8'))
    res = tel.read_until(b'# ',     TIMEOUT).decode('utf-8').split('\r\n')
    res.pop(0)
    res.pop(-1)

    error = '\n'.join(res)

    if error != '':
        raise RuntimeError(error)


if __name__ == '__main__':

    opt = docopt(__doc__)

    if opt.get('-c'):
        conf_file = opt.get('CONF')
    else:
        conf_file =  os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            DEFAULT_CONF_FILE
        )

    config = yaml.load(open(conf_file, 'r'), Loader=yaml.BaseLoader)

    try:
        yamaha_usb_ctrl(config, opt.get('ADDR'), opt.get('MODE').lower(), True)
        print('\033[1;32m%s\033[0m' % ('SUCESS'))
        sys.exit(0)
    except RuntimeError as e:
        print('\033[1;31m%s\033[0m' % ('FAIL'))
        print(e.args[0])
        sys.exit(-1)
