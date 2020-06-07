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
import  sys

DEFAULT_CONF_FILE = 'yamaha_config.yml'
TIMEOUT           = 2

opt = docopt(__doc__)

if opt.get('-c'):
    conf_file = opt.get('CONF')
else:
    conf_file = DEFAULT_CONF_FILE

config = yaml.load(open(conf_file, 'r'), Loader=yaml.BaseLoader)

print('Login        ... ', end='')
tel = telnetlib.Telnet(opt.get('ADDR'))
tel.read_until(b'Password:')
tel.write((config['pass'] + '\n').encode('utf-8'))
tel.read_until(b'> ')
print('OK')

print('Enable admin ... ', end='')
tel.write(b'admin\n')
tel.read_until(b'Password:')
tel.write((config['admin'] + '\n').encode('utf-8'))
tel.read_until(b'# ')
print('OK')

tel.write(('usbhost use %s\n' % (opt.get('MODE').lower())).encode('utf-8'))
res = tel.read_until(b'# ',     TIMEOUT).decode('utf-8').split('\r\n')
res.pop(0)
res.pop(-1)

error = '\n'.join(res)

if error == '':
    print('\033[1;32m%s\033[0m' % ('SUCESS'))
    sys.exit(0)
else:
    print('\033[1;31m%s\033[0m' % ('FAIL'))
    print(error)
    sys.exit(-1)


