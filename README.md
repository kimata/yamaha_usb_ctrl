# yamaha_usb_ctrl

## 機能

YAMAH のルータにログインして，USB の ON/OFF を制御するスクリプトです．
USB の電源端子を 5V I/O の用に活用することが可能になります．

## 使い方

`lib/yamaha_usb_ctrl.py' を実行すると使い方が表示されます．

## サンプルアプリ

app ディレクトリに，InfluxDB にあるデータを基に USB を ON/OFF するサンプルアプリが入っています．
USB を ON することで，冷却ファンが動作するようになっていることを想定しています．
