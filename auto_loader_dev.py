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
import sys

import psycopg2
import requests
from pyautogui import FailSafeException

import auto_input.autoscope
import auto_input.xcope
import config_dev as config
import scan.scanner
import tray_task.tray_task
from hospital_info import data_processing
from utils import http_request
from utils import logger  # 导入新的日志模块
from window.prompt_dialog_box import error_window

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
    logger.info("开始检查扫描器结束符设置")
    qr_code_scanner = scan.scanner.Scanner(config.SERIAL_PORT, config.BAUDRATE)
    data = qr_code_scanner.get_scanner_content()
    match data:
        case "扫描器设置完成测试":
            print("设置成功")
            logger.info("扫描器结束符设置正确")
        case "扫描器设置完成测试\r":
            print(f"缺少设置没有结束符号,原始数据为:{repr(data)}")
            logger.warning(f"扫描器缺少结束符设置，原始数据为:{repr(data)}")
        case _:
            print(f"没有匹配到任何参数,原始数据为:{repr(data)}")
            logger.warning(f"扫描器设置检查异常，未匹配到预期内容，原始数据为:{repr(data)}")

def is_tj_starting(string):
    pattern = r"^TJ"
    return bool(re.match(pattern, string))

@logger.log_function_call()  # 使用日志装饰器记录函数调用
def main():
    # 初始化日志系统
    logger.setup_logging(
        log_level=logger.LOG_LEVEL_DEBUG,  # 开发版使用DEBUG级别
        log_file_prefix="autoloader_dev",
        max_bytes=10*1024*1024,  # 10MB
        backup_count=5,
        console_output=True  # 开发版输出到控制台
    )
    
    logger.info("===== AutoLoader 程序启动 =====")
    logger.info(f"运行环境: 开发模式 (DEV_MODE = {config.DEV_MODE})")
    
    if config.VPN_MODE:
        logger.info("VPN模式已启用，将尝试连接医院内网资源")
    else:
        logger.warning("VPN模式已禁用，将无法连接医院内网资源")
        
    # 托盘栏
    logger.info("初始化系统托盘...")
    tray = tray_task.tray_task.TrayTask()
    threading.Thread(target=tray.setup_systray, daemon=True).start()
    
    # 连接扫描器
    logger.info(f"连接扫描器 (端口: {config.SERIAL_PORT}, 波特率: {config.BAUDRATE})...")
    try:
        qr_code_scanner = scan.scanner.Scanner(config.SERIAL_PORT, config.BAUDRATE)
        if not qr_code_scanner.is_open():
            # 扫描器打开失败进行提示
            logger.critical(f"扫描器连接失败，端口:{config.SERIAL_PORT}, 波特率:{config.BAUDRATE}")
            error_window(f"扫描器连接失败，请检查连接或修改CONFIG.py中的参数\n"
                         f"当前端口:{config.SERIAL_PORT}, 波特率:{config.BAUDRATE}", 500, 150)
            logger.info("程序退出 - 原因: 扫描器连接失败")
            return
        logger.info("扫描器连接成功")
    except Exception as e:
        logger.critical(f"扫描器连接异常: {str(e)}")
        error_window(f"扫描器连接异常，请检查连接或修改CONFIG.py中的参数\n"
                     f"当前端口:{config.SERIAL_PORT}, 波特率:{config.BAUDRATE}\n"
                     f"异常信息: {str(e)}", 500, 180)
        logger.info("程序退出 - 原因: 扫描器连接异常")
        return

    # 用来存储序列号，在界面上显示
    current_patient = {'serial_number': 0}

    # 连接pg
    pg_conn = None
    if config.VPN_MODE:
        logger.info(f"尝试连接PostgreSQL数据库 (主机: {config.POSTGRES_HOST}, 端口: {config.POSTGRES_PORT})...")
        try:
            pg_conn = psycopg2.connect(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                user=config.POSTGRES_USERNAME,
                password=config.POSTGRES_PASSWORD,
                database=config.POSTGRES_DATABASE
            )
            logger.info("PostgreSQL数据库连接成功")
        except Exception as e:
            logger.critical(f"PostgreSQL数据库连接失败: {str(e)}")
            error_window(f"连接PostgreSQL数据库发生异常，请检查网络连接或修改CONFIG.py中的参数\n"
                        f"主机地址:{config.POSTGRES_HOST}, 端口:{config.POSTGRES_PORT}\n"
                        f"异常信息: {str(e)}", 500, 200)
            logger.info("程序退出 - 原因: 数据库连接失败")
            return
    else:
        logger.warning("VPN模式已禁用，跳过数据库连接")

    # 测试自动填表
    logger.info("测试自动填表功能...")
    try:
        auto_input.xcope.input_test()
        logger.info("自动填表功能测试成功")
    except Exception as e:
        logger.error(f"自动填表测试失败: {str(e)}")
        error_window(f"自动填表测试失败，请检查系统环境\n"
                     f"异常信息: {str(e)}\n"
                     f"程序将继续运行，但可能无法正常工作", 500, 200)

    # 轮询
    logger.info("进入主循环，等待扫描器输入...")
    try:
        while True:
            try:
                # 获取扫描的内容
                scanner_result = qr_code_scanner.get_scanner_content()
                logger.info(f"扫描器输入: {scanner_result}")

                # 检查是否为回退特殊指令
                if scanner_result == "AutoLoaderRollback":
                    current_patient['serial_number'] -= 1
                    logger.info(f"执行回退操作，当前序号变更为: {current_patient['serial_number']}")
                    continue

                # 根据是否是TJ开头区分是体检系统还是主系统抽血
                if is_tj_starting(scanner_result):
                    logger.info(f"检测到体检系统条码: {scanner_result}")
                    # 体检系统的流程
                    try:
                        # 体检系统
                        # 生成序列号
                        current_patient['serial_number'] += 1
                        current_time = datetime.datetime.now().strftime("%Y%m%d")
                        serial_number = f"{current_time}S{str(current_patient['serial_number']).zfill(6)}"
                        logger.info(f"生成新序列号: {serial_number}")
                        
                        # 从PG中读取病人数据
                        if config.VPN_MODE and pg_conn:
                            logger.debug("尝试从PostgreSQL数据库获取患者信息")
                            data = data_processing.check_patient_message(scanner_result, pg_conn)
                        else:
                            logger.debug("VPN模式禁用，使用模拟患者数据")
                            # 开发模式使用模拟数据
                            data = {
                                'patient_name': '张三(开发模式)',
                                'test_type': '阴道分泌物检查(模拟)',
                                'patient_sex': '女',
                                'birth_date': '1990-01-01',
                                'patient_age': '33'
                            }
                            
                        if data:
                            logger.info(f"获取到患者信息: {data['patient_name']}")
                            auto_input.autoscope.input_message(serial_number, data["patient_name"],
                                                            data["test_type"], data["patient_sex"],
                                                            data["birth_date"], data["patient_age"])
                        else:
                            logger.warning(f"未找到患者信息: {scanner_result}")
                            error_window(f"未找到患者信息，请检查扫描条码是否正确\n条码: {scanner_result}", 500, 150)

                    except Exception as e:
                        logger.error(f"处理体检系统条码异常: {str(e)}", exc_info=True)
                        error_window(f"处理体检系统条码异常，请重试\n条码: {scanner_result}\n异常信息: {str(e)}", 500, 180)

                else:
                    logger.info(f"检测到医院HIS系统条码: {scanner_result}")
                    # HIS系统的流程
                    try:
                        # His系统
                        # 生成序列号
                        current_patient['serial_number'] += 1
                        current_time = datetime.datetime.now().strftime("%Y%m%d")
                        serial_number = f"{current_time}S{str(current_patient['serial_number']).zfill(6)}"
                        logger.info(f"生成新序列号: {serial_number}")

                        if config.VPN_MODE:
                            logger.debug("尝试从HIS系统获取患者信息")
                            data = data_processing.check_patient_his_message(scanner_result)
                        else:
                            logger.debug("VPN模式禁用，使用模拟HIS患者数据")
                            # 开发模式使用模拟数据
                            data = {
                                'patient_name': '李四(开发模式)',
                                'visit_id': scanner_result,
                                'patient_sex': '男',
                                'birth_date': '1985-05-05',
                                'patient_age': '38',
                                'dept_name': '内科(模拟)',
                                'dept_no': 'N001'
                            }
                            
                        if data:
                            logger.info(f"获取到患者信息: {data['patient_name']}")
                            auto_input.xcope.input_message(serial_number, data["patient_name"],
                                                        data["visit_id"], data["patient_sex"],
                                                        data["birth_date"], data["patient_age"],
                                                        data["dept_name"], data["dept_no"])
                        else:
                            logger.warning(f"未找到患者HIS信息: {scanner_result}")
                            error_window(f"未找到患者HIS信息，请检查扫描条码是否正确\n条码: {scanner_result}", 500, 150)

                    except Exception as e:
                        logger.error(f"处理医院HIS系统条码异常: {str(e)}", exc_info=True)
                        error_window(f"处理医院HIS系统条码异常，请重试\n条码: {scanner_result}\n异常信息: {str(e)}", 500, 180)

            except FailSafeException:
                logger.warning("触发PyAutoGUI故障安全异常 - 鼠标移动到屏幕角落")
                error_window("自动填表过程中检测到鼠标移动到屏幕角落，自动操作已中断\n请避免在操作过程中移动鼠标", 500, 150)
            except Exception as e:
                logger.error(f"主循环异常: {str(e)}", exc_info=True)
                error_window(f"发生意外异常，请重试\n异常信息: {str(e)}", 500, 150)

    except KeyboardInterrupt:
        logger.info("检测到键盘中断，程序正常退出")
    except Exception as e:
        logger.critical(f"程序异常退出: {str(e)}", exc_info=True)
        error_window(f"程序异常退出\n异常信息: {str(e)}", 500, 150)
    finally:
        # 关闭连接
        try:
            if pg_conn:
                pg_conn.close()
                logger.info("PostgreSQL数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接异常: {str(e)}")
            
        try:
            if 'qr_code_scanner' in locals() and qr_code_scanner:
                qr_code_scanner.close()
                logger.info("扫描器连接已关闭")
        except Exception as e:
            logger.error(f"关闭扫描器连接异常: {str(e)}")
            
        logger.info("===== AutoLoader 程序结束 =====")


if __name__ == '__main__':
    # 注册信号处理，确保程序能够优雅退出
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    try:
        # 尝试清理过期日志文件（保留30天）
        logger.cleanup_logs(days_to_keep=30)
    except Exception as e:
        print(f"清理日志文件失败: {str(e)}")
        
    main() 