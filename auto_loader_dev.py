"""
AutoLoader开发版本
这个文件是auto_loader.py的开发环境友好版本
在macOS和Linux等非Windows环境下使用此文件进行测试
"""

import datetime
import json
import os
import re
import signal
import threading
import time

import psycopg2
import requests

# 使用开发环境配置
try:
    import config_dev as config
    print("[DEV] 使用开发环境配置")
except ImportError:
    import config
    print("[DEV] 警告: 使用生产环境配置，连接可能需要较长时间")

from hospital_info import data_processing
from utils import http_request

# 开发模式下不使用实际扫描器，使用模拟输入
class DevScanner:
    def __init__(self, serial_port, baudrate, timeout=0):
        print(f"[DEV] 初始化模拟扫描器 (实际串口:{serial_port}, 波特率:{baudrate})")
        self.__is_open = True

    def is_open(self) -> bool:
        return self.__is_open

    def open(self):
        self.__is_open = True
        print("[DEV] 模拟扫描器已打开")

    def close(self):
        self.__is_open = False
        print("[DEV] 模拟扫描器已关闭")

    def get_scanner_content(self) -> str:
        print("\n" + "="*50)
        print("[DEV] 模拟扫描器等待输入")
        print("="*50)
        print("请输入模拟扫描内容:")
        print("- 输入 'TJ12345' 模拟体检条码")
        print("- 输入其他字符串模拟诊疗卡号")
        print("- 输入 'AutoLoaderRollback' 回退编号")
        print("- 输入 'exit' 退出程序")
        print("="*50)
        
        content = input(">> ")
        
        if content.lower() == 'exit':
            print("[DEV] 用户请求退出程序")
            import os, signal
            pid = os.getpid()
            os.kill(pid, signal.SIGTERM)
            
        return content

# 开发模式下不弹出实际窗口，只在控制台显示
def dev_error_window(message: str, window_width: int | str, window_height: int | str):
    print("\n" + "="*50)
    print("[DEV] 错误提示窗口")
    print("="*50)
    print(f"消息: {message}")
    print(f"窗口尺寸: {window_width}x{window_height}")
    print("="*50)
    print("按Enter键继续...")
    input()

# 开发模式下不创建系统托盘
class DevTrayTask:
    def __init__(self):
        print("[DEV] 初始化模拟系统托盘")
    
    def setup_systray(self):
        print("[DEV] 模拟系统托盘已启动")
    
    def quit_application(self):
        print("[DEV] 用户通过系统托盘请求退出")
        import os, signal
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)

def check_end_mark():
    """
    检测是否忘记设置结束符，由于结束符在打印的时候也看不到，所以需要认真查看
    """
    scanner = DevScanner(config.SERIAL_PORT, config.BAUDRATE)
    data = scanner.get_scanner_content()
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
    # 托盘栏 - 开发模式下简化实现
    tray = DevTrayTask()
    tray.setup_systray()
    
    # 连接扫描器 - 开发模式下使用模拟扫描器
    qr_code_scanner = DevScanner(config.SERIAL_PORT, config.BAUDRATE)
    
    # 尝试连接数据库
    try:
        # 在开发模式下提供友好错误处理
        try:
            # 如果是开发模式，使用更短的连接超时
            connect_timeout = 2 if hasattr(config, 'DEV_MODE') and config.DEV_MODE else 30
            connection = psycopg2.connect(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                user=config.POSTGRES_USERNAME,
                password=config.POSTGRES_PASSWORD,
                database=config.POSTGRES_DATABASE,
                connect_timeout=connect_timeout  # 开发模式下使用短超时
            )
            cursor = connection.cursor()
            print("[DEV] 成功连接到PostgreSQL数据库")
        except (psycopg2.Error, Exception) as e:
            # 开发模式下使用模拟数据库环境
            print(f"[DEV] 数据库连接失败：{e}")
            if hasattr(config, 'VPN_MODE') and config.VPN_MODE:
                print("[DEV] VPN模式连接失败，可能是VPN未连接或网络问题")
                print("[DEV] 请检查VPN连接状态或切换回普通开发模式")
            print("[DEV] 使用模拟数据库环境...")
            
            class MockCursor:
                def __init__(self):
                    # 模拟患者数据库
                    self.patients_db = {
                        '123456': ('123456', '张三', '45', '妇科', '李医生'),
                        '234567': ('234567', '李四', '32', '内科', '王医生'),
                        '345678': ('345678', '王五', '28', '外科', '赵医生'),
                        '456789': ('456789', '赵六', '50', '急诊', '钱医生'),
                        '567890': ('567890', '钱七', '36', '儿科', '孙医生'),
                        '00001719': ('00001719', '测试患者', '40', '妇科', '测试医生'),
                    }
                    # 有多个匹配项的测试用例
                    self.multiple_matches = ['999999', '888888']
                    # 模拟不存在的病例
                    self.not_found = ['111111', '222222', '000000']
                
                def execute(self, query):
                    print(f"[DEV] 执行SQL: {query}")
                    self.last_query = query
                    return self
                
                def fetchall(self):
                    print("[DEV] 返回模拟数据...")
                    # 解析SQL查询中的诊疗卡号
                    import re
                    card_match = re.search(r"JIUZHENKH='([^']+)'", self.last_query)
                    if not card_match:
                        return []
                    
                    card_number = card_match.group(1)
                    
                    # 检查是否是特殊测试案例
                    if card_number in self.multiple_matches:
                        # 返回多条记录模拟多个匹配情况
                        return [
                            (card_number, f'测试患者1', '30', '测试科室', '测试医生'),
                            (card_number, f'测试患者2', '35', '测试科室', '测试医生')
                        ]
                    elif card_number in self.not_found:
                        # 返回空记录模拟未找到记录
                        return []
                    elif card_number in self.patients_db:
                        # 返回匹配的患者记录
                        return [self.patients_db[card_number]]
                    else:
                        # 默认返回一个通用记录
                        return [(card_number, f'模拟患者_{card_number[-4:]}', '35', '妇科', '模拟医生')]
            
            class MockConnection:
                def cursor(self):
                    return MockCursor()
            
            connection = MockConnection()
            cursor = connection.cursor()
    except Exception as e:
        dev_error_window(f"连接数据库失败: {e}", 900, 300)
        raise e

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

    print("[DEV] AutoLoader初始化完成，开始运行主循环...")
    while True:
        scann_data = qr_code_scanner.get_scanner_content()

        if scann_data == "AutoLoaderRollback":
            data["sample_number"] = data["sample_number"] - 1
            dev_error_window("样本编号已减少1", 600, 270)
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
            print(f"[DEV] 检测到体检条码: {scann_data}")
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
                print("[DEV] 尝试从体检系统获取数据...")
                # 开发模式下不实际发送请求，使用模拟数据
                # response = http_request.get_response("POST", url, 1, 10, verify=False, headers=headers, data=payload)
                
                # 模拟响应
                class MockResponse:
                    @property
                    def text(self):
                        return json.dumps({
                            "msg": "发送成功",
                            "code": "1001",
                            "data": [
                                {
                                    "name": "测试患者",
                                    "age": 45,
                                    "checkCode": scann_data,
                                    "applyDct": "测试医生",
                                    "departName": "体检中心"
                                }
                            ]
                        })
                
                response = MockResponse()
                print("[DEV] 成功获取模拟数据")
                
            except Exception as e:
                data["sample_number"] = sample_number - 1
                dev_error_window(f"获取数据失败,请稍后再尝试,错误码:3 - {str(e)}", 900, 270)
                continue
                
            patient_info = data_processing.json_to_dict(response.text).get('data')
            if not patient_info:
                data["sample_number"] = sample_number - 1
                dev_error_window("体检系统查询不到该病人数据，错误码:2", 900, 270)
                continue
            else:
                patient_info = patient_info[0]
                
            xcope_xm = patient_info.get('name')
            xcope_nl = patient_info.get('age')
            xcope_zlkh = patient_info.get('checkCode')
            xcope_sjys = patient_info.get('applyDct')
            xcope_sjks = patient_info.get('departName')
            xcope_ybbh = f"M{now_year}{str(sample_number).zfill(5)}"
            data["sample_number"] = sample_number
            
            # 在开发模式下只显示结果，不实际操作界面
            print("\n" + "="*50)
            print("[DEV] 自动输入以下信息:")
            print("="*50)
            print(f"姓名: {xcope_xm}")
            print(f"年龄: {xcope_nl}")
            print(f"诊疗卡号: {xcope_zlkh}")
            print(f"样本编号: {xcope_ybbh}")
            print(f"送检医师: {xcope_sjys}")
            print(f"送检科室: {xcope_sjks}")
            print("="*50)
            
            with open(data_file_path, 'w') as file:
                json.dump(data, file)
        else:
            print(f"[DEV] 检测到诊疗卡号: {scann_data}")
            sql = f"SELECT JIUZHENKH,XINGMING,NIANLING,KESHIMC,KAIDANREN FROM v_binglikaidan_bingrenxx WHERE JIUZHENKH='{scann_data}'"
            try:
                print(f"[DEV] 执行SQL查询: {sql}")
                cursor.execute(sql)
                patient_infos = cursor.fetchall()
                print(f"[DEV] 查询结果: {patient_infos}")
            except Exception as e:
                dev_error_window(f"数据库查询失败: {e}", 900, 300)
                continue
                
            length = len(patient_infos)
            if length == 1:
                patient_info = patient_infos[0]
                xcope_xm = patient_info[1]
                xcope_nl = patient_info[2]
                xcope_zlkh = patient_info[0]
                xcope_ybbh = f"M{now_year}{str(sample_number).zfill(5)}"
                data["sample_number"] = sample_number
                xcope_sjys = patient_info[4]
                xcope_sjks = patient_info[3]
                
                # 在开发模式下只显示结果，不实际操作界面
                print("\n" + "="*50)
                print("[DEV] 自动输入以下信息:")
                print("="*50)
                print(f"姓名: {xcope_xm}")
                print(f"年龄: {xcope_nl}")
                print(f"诊疗卡号: {xcope_zlkh}")
                print(f"样本编号: {xcope_ybbh}")
                print(f"送检医师: {xcope_sjys}")
                print(f"送检科室: {xcope_sjks}")
                print("="*50)
                
                with open(data_file_path, 'w') as file:
                    json.dump(data, file)
            elif length == 0:
                data["sample_number"] = sample_number - 1
                dev_error_window("该号码在数据库查询不到", 600, 270)
                continue
            else:
                data["sample_number"] = sample_number - 1
                dev_error_window("该号码在数据库存在多个,无法自动输入", 600, 270)
                continue


if __name__ == '__main__':
    try:
        print("\n" + "="*50)
        print("AutoLoader 开发模式")
        print("="*50)
        print("此版本专为开发环境设计，不包含实际自动化操作")
        print("- 数据库连接: 尝试真实连接，失败时使用模拟数据")
        print("- 扫描器: 使用控制台输入模拟")
        print("- 用户界面: 使用控制台输出代替图形界面")
        print("="*50 + "\n")
        
        main()
    except KeyboardInterrupt:
        print("\n[DEV] 用户中断程序")
    except Exception as e:
        print(f"\n[DEV] 程序异常退出: {e}")
    finally:
        print("\n[DEV] 程序已退出") 