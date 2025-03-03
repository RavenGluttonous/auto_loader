import datetime
import json
import os
import re
import signal
import threading
import time

import psycopg2
import requests
from pyautogui import FailSafeException

import auto_input.autoscope
import auto_input.xcope
import config
import scan.scanner
import tray_task.tray_task
from hospital_info import data_processing
from utils import http_request
from window.prompt_dialog_box import error_window


def check_end_mark():
    """
    检测是否忘记设置结束符，由于结束符在打印的时候也看不到，所以需要认真查看

    """
    qr_code_scanner = scan.scanner.Scanner(config.SERIAL_PORT, config.BAUDRATE)
    data = qr_code_scanner.get_scanner_content()
    match data:
        case "扫描器设置完成测试":
            print("设置成功")
        case "扫描器设置完成测试\r":
            print(f"缺少设置没有结束符号,原始数据为:{repr(data)}")
        case _:
            print(f"没有匹配到任何参数,原始数据为:{repr(data)}")


def is_tj_starting(string):
    pattern = r"^TJ"
    return bool(re.match(pattern, string))


def main():
    # 避免平板开机网络连接有问题增加延迟
    time.sleep(10)
    # 托盘栏
    tray = tray_task.tray_task.TrayTask()
    threading.Thread(target=tray.setup_systray, daemon=True).start()
    # 连接扫描器
    qr_code_scanner = scan.scanner.Scanner(config.SERIAL_PORT, config.BAUDRATE)
    # 连接数据库
    try:
        connection = psycopg2.connect(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            user=config.POSTGRES_USERNAME,
            password=config.POSTGRES_PASSWORD,
            database=config.POSTGRES_DATABASE
        )
        cursor = connection.cursor()
    except psycopg2.Error as e:
        error_window(f"连接PostgreSQL数据库失败，程序退出，点击确认后会自动重启启动，请等待2分钟", 900, 300)
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)
    # 样本编号相关
    data_dir_path = r".\data"
    if not os.path.exists(data_dir_path):
        os.makedirs(data_dir_path)
    data_file_path = os.path.join(data_dir_path, "data.json")
    now_time = datetime.datetime.now()
    now_year = now_time.year
    # data.json文件存在
    if os.path.isfile(data_file_path):
        with open(data_file_path, 'r') as file:
            data = json.load(file)
    # data.json文件不存在，给与默认值
    else:
        data = {"sample_number": 0, "year": now_year}
        with open(data_file_path, 'w') as file:
            json.dump(data, file)
    record_year = data["year"]

    while True:
        scann_data = qr_code_scanner.get_scanner_content()

        if scann_data == "AutoLoaderRollback":
            data["sample_number"] = data["sample_number"] - 1
            error_window("样本编号已减少1", 600, 270)
            continue
        now_time = datetime.datetime.now()
        now_year = now_time.year
        if now_year != record_year:
            data = {"sample_number": 0, "year": now_year}
            record_year = data["year"]
            with open(data_file_path, 'w') as file:
                json.dump(data, file)
        sample_number = data["sample_number"] + 1
        if is_tj_starting(scann_data):
            url = "http://192.168.0.17:18838/api/public/open/json/checkAppInfoQuery"
            payload = json.dumps({
                "hospCode": "tlsrmyy",
                "checkCode": f"{scann_data}",
                "applyType": "PACS",
                "checkType": "阴道分泌物荧光检查",
                "startTime": "",
                "endTime": ""
            })
            headers = {
                'Content-Type': 'application/json'
            }
            try:
                response = http_request.get_response("POST", url, 1, 10, verify=False, headers=headers,
                                                     data=payload)
            except requests.exceptions as e:
                data["sample_number"] = sample_number - 1
                error_window(f"获取数据失败,请稍后再尝试,错误码:3", 900, 270)
                continue
            if response is None:
                data["sample_number"] = sample_number - 1
                error_window(f"获取不到体检病人数据,请稍后再尝试,错误码:1", 900, 270)
                continue
            patient_info = data_processing.json_to_dict(response.text).get('data')
            if not patient_info:
                data["sample_number"] = sample_number - 1
                error_window("体检系统查询不到该病人数据，错误码:2", 900, 270)
                continue
            else:
                patient_info = patient_info[0]
            xcope_xm = patient_info.get('name')
            # xcope年龄
            xcope_nl = patient_info.get('age')
            # xcope诊疗卡号
            xcope_zlkh = patient_info.get('checkCode')
            # xcope送检医师
            xcope_sjys = patient_info.get('applyDct')
            # xcope送检科室
            xcope_sjks = patient_info.get('departName')
            # xcope样本编号
            xcope_ybbh = f"M{now_year}{str(sample_number).zfill(5)}"
            data["sample_number"] = sample_number
            try:
                auto_input.xcope.xcope_input(xm=xcope_xm, nl=xcope_nl, zlkh=xcope_zlkh, sjys=xcope_sjys,
                                             sjks=xcope_sjks,ybbh=xcope_ybbh)
            except FailSafeException as e:
                data["sample_number"] = sample_number - 1
                error_window("自动输入过程，鼠标光标请不要移动到屏幕的四个角落，请移动回正确位置再重新扫描。", 900,
                             300)
                continue
            with open(data_file_path, 'w') as file:
                json.dump(data, file)
        else:
            sql = f"SELECT JIUZHENKH,XINGMING,NIANLING,KESHIMC,KAIDANREN FROM v_binglikaidan_bingrenxx WHERE JIUZHENKH='{scann_data}'"
            try:
                cursor.execute(sql)
                patient_infos = cursor.fetchall()
            except psycopg2.Error as e:
                error_window(f"连接PostgreSQL数据库失败，程序退出，点击确认后会自动重启启动，请等待2分钟", 900, 300)
                pid = os.getpid()
                os.kill(pid, signal.SIGTERM)
            length = len(patient_infos)
            if length == 1:
                patient_info = patient_infos[0]
                # xcope姓名
                xcope_xm = patient_info[1]
                # xcope年龄
                xcope_nl = patient_info[2]
                # xcope诊疗卡号
                xcope_zlkh = patient_info[0]
                # xcope样本编号
                xcope_ybbh = f"M{now_year}{str(sample_number).zfill(5)}"
                data["sample_number"] = sample_number
                # xcope送检医师
                xcope_sjys = patient_info[4]
                # xcope送检科室
                xcope_sjks = patient_info[3]
                try:
                    auto_input.xcope.xcope_input(xm=xcope_xm, nl=xcope_nl, zlkh=xcope_zlkh, sjys=xcope_sjys,
                                                 sjks=xcope_sjks,
                                                 ybbh=xcope_ybbh)
                except FailSafeException as e:
                    data["sample_number"] = sample_number - 1
                    error_window("自动输入过程，鼠标光标请不要移动到屏幕的四个角落，请移动回正确位置再重新扫描。", 900,
                                 300)
                    continue
                with open(data_file_path, 'w') as file:
                    json.dump(data, file)
            elif length == 0:
                data["sample_number"] = sample_number - 1
                error_window("该号码在数据库查询不到", 600, 270)
                continue
            else:
                data["sample_number"] = sample_number - 1
                error_window("该号码在数据库存在多个,无法自动输入", 600, 270)
                continue


if __name__ == '__main__':
    main()
