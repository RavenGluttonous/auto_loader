import base64
import datetime
import json
import os
import re
import signal
import threading
import time
import sys

# import psycopg2  # PostgreSQL 已停用，仅保留导入语句供参考
import requests
from pyautogui import FailSafeException

import auto_input.autoscope
import auto_input.xcope
import config
import scan.scanner
import tray_task.tray_task
from hospital_info import data_processing
from utils import http_request
from utils import logger  # 导入新的日志模块
from xcope_client import XcopeClient
from register_document_client import RegisterDocumentClient

# Xcope 报告轮询相关全局变量
_XCOPE_CLIENT: XcopeClient | None = None
_XCOPE_POLL_THREAD: threading.Thread | None = None
_XCOPE_POLL_STOP = threading.Event()
_XCOPE_PROCESSED_IDS_LOCK = threading.Lock()
_XCOPE_PROCESSED_IDS: set[str] = set()
_XCOPE_LAST_SCANNER_CODE_LOCK = threading.Lock()
_XCOPE_LAST_SCANNER_CODE: str | None = None

from window.prompt_dialog_box import error_window




def _ensure_xcope_client() -> XcopeClient | None:
    global _XCOPE_CLIENT
    if _XCOPE_CLIENT is None:
        _XCOPE_CLIENT = XcopeClient(
            base_url=config.XCOPE_BASE_URL,
            client_id=config.XCOPE_CLIENT_ID,
            client_secret=config.XCOPE_CLIENT_SECRET,
            scope=config.XCOPE_SCOPE,
        )
    return _XCOPE_CLIENT


def _set_last_scanner_code(code: str) -> None:
    global _XCOPE_LAST_SCANNER_CODE
    with _XCOPE_LAST_SCANNER_CODE_LOCK:
        _XCOPE_LAST_SCANNER_CODE = code.strip()


def _get_last_scanner_code() -> str | None:
    with _XCOPE_LAST_SCANNER_CODE_LOCK:
        return _XCOPE_LAST_SCANNER_CODE


def _mark_report_processed(report_id: str) -> None:
    with _XCOPE_PROCESSED_IDS_LOCK:
        _XCOPE_PROCESSED_IDS.add(report_id)


def _is_report_processed(report_id: str) -> bool:
    with _XCOPE_PROCESSED_IDS_LOCK:
        return report_id in _XCOPE_PROCESSED_IDS


def _xcope_poll_worker() -> None:
    """每3秒轮询一次 Xcope 报告列表并下载 PDF，去重处理。

    - startDate/EndDate 为当天时间
    - MaxResultCount 默认99999
    - 使用获取到的条码作为PDF文件名，保存到 D:\\东华病理报告
    - 报告和PDF根据 report Id 去重
    """
    logger.info("Xcope 报告轮询线程启动")
    client = _ensure_xcope_client()
    if client is None:
        logger.error("XcopeClient 初始化失败，轮询线程退出")
        return

    base_dir = r"D:\\东华病理报告"
    os.makedirs(base_dir, exist_ok=True)

    register_client = RegisterDocumentClient()

    while not _XCOPE_POLL_STOP.is_set():
        try:
            last_code = _get_last_scanner_code()
            if not last_code:
                # 当前还没有条码，不做任何事情
                time.sleep(3)
                continue

            items = client.get_today_report_list(max_result_count=99999)
            logger.info(f"Xcope 今日报告总数: {len(items)}")

            # 本轮需要反馈的平台文档信息列表（去重后）
            to_register: list[dict] = []

            for item in items:
                report_id = str(item.get("Id") or "").strip()
                if not report_id:
                    continue
                if _is_report_processed(report_id):
                    continue

                pdf_bytes = client.download_report_pdf(report_id)
                if not pdf_bytes:
                    continue

                # 使用最近一次扫码获取的条码和报告Id作为文件名，支持一条码多报告多文件
                filename = f"{last_code}_{report_id}.pdf"
                filepath = os.path.join(base_dir, filename)

                try:
                    with open(filepath, "wb") as f:
                        f.write(pdf_bytes)
                    logger.info(f"已保存 Xcope 报告 PDF: {filepath}")
                    _mark_report_processed(report_id)

                    to_register.append(
                        {
                            "report_id": report_id,
                            "filepath": filepath,
                            "item": item,
                        }
                    )
                except Exception as e:
                    logger.error(f"保存 Xcope 报告 PDF 失败: {filepath}, 错误: {e}")

            # 当列表数据全部操作完后，再调用反馈接口
            for info in to_register:
                _register_document_for_report(register_client, info["report_id"], info["filepath"], info["item"], last_code)

        except Exception as e:
            logger.error(f"Xcope 报告轮询线程异常: {e}", exc_info=True)

        # 每3秒执行一次
        time.sleep(3)



def _register_document_for_report(register_client: RegisterDocumentClient, report_id: str, filepath: str, item: dict, barcode: str) -> None:
    """将单条报告使用 RegisterDocument 反馈给医院平台。

    当前实现：
    - 使用 Xcope 报告 Id 作为 DocumentID
    - 使用本地 PDF 路径作为 DocumentPath（后续可根据医院平台要求改为HTTP地址）
    - 其他字段从 item 中尽量提取，如获取不到则置空
    """
    try:
        # 生成消息ID、日期、时间
        now = datetime.datetime.now()
        message_id = f"REG-{now.strftime('%Y%m%d%H%M%S')}-{report_id}"
        update_date = now.strftime("%Y-%m-%d")
        update_time = now.strftime("%H:%M:%S")

        # 读入PDF并转为Base64
        try:
            with open(filepath, "rb") as f:
                pdf_bytes = f.read()
            document_content_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"读取 PDF 文件失败，无法进行文档注册: {filepath}, 错误: {e}")
            return

        # 从 Xcope 报告 item 中尽量提取患者及就诊信息（字段名为中文，示例中采用常见字段名）
        pat_patient_id = str(item.get("诊疗卡号") or "")
        pat_patient_name = str(item.get("姓名") or "")
        paadm_visit_number = str(item.get("就诊流水号") or "")
        specimen_id = str(item.get("样本编号") or "")
        oeori_order_item_id = str(item.get("医嘱ID") or "")

        # 如果 Xcope 返回中没有上述字段，可以根据实际字段名调整

        success = register_client.register_document(
            message_id=message_id,
            organization_code="0001",
            pat_patient_id=pat_patient_id,
            pat_patient_name=pat_patient_name,
            paadm_visit_number=paadm_visit_number,
            specimen_id=specimen_id,
            oeori_order_item_id=oeori_order_item_id,
            document_type="02006",  # 病理报告
            document_id=report_id,
            document_content_base64=document_content_base64,
            document_path=filepath,
            document_pic_path="",  # 如有需要可根据实际情况填写
            update_user_code="AutoLoader",
            update_date=update_date,
            update_time=update_time,
        )

        if success:
            logger.info(f"文档注册成功，报告Id={report_id}，条码={barcode}")
            # 注册成功后，删除本地PDF文件，避免磁盘堆积
            try:
                os.remove(filepath)
                logger.info(f"已删除本地PDF文件: {filepath}")
            except OSError as oe:
                logger.warning(f"删除本地PDF文件失败: {filepath}，错误: {oe}")
        else:
            logger.error(f"文档注册失败，报告Id={report_id}，条码={barcode}")

    except Exception as e:
        logger.error(f"文档注册过程中发生异常，报告Id={report_id}，条码={barcode}，错误: {e}", exc_info=True)

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


# def is_tj_starting(string):
#     pattern = r"^TJ"
#     return bool(re.match(pattern, string))


@logger.log_function_call()  # 使用日志装饰器记录函数调用
def main():
    # 初始化日志系统
    logger.setup_logging(
        log_level=logger.LOG_LEVEL_INFO,
        log_file_prefix="autoloader",
        max_bytes=10*1024*1024,  # 10MB
        backup_count=5
    )

    logger.info("===== AutoLoader 程序启动 =====")
    logger.info(f"运行环境: 主程序模式")

    # 避免平板开机网络连接有问题增加延迟
    logger.info("等待网络连接稳定，延迟10秒...")
    time.sleep(10)

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

    # 连接pg（已停用，仅保留代码供参考）
    # logger.info(f"连接PostgreSQL数据库 (主机: {config.POSTGRES_HOST}, 端口: {config.POSTGRES_PORT})...")
    # try:
    #     pg_conn = psycopg2.connect(
    #         host=config.POSTGRES_HOST,
    #         port=config.POSTGRES_PORT,
    #         user=config.POSTGRES_USERNAME,
    #         password=config.POSTGRES_PASSWORD,
    #         database=config.POSTGRES_DATABASE
    #     )
    #     logger.info("PostgreSQL数据库连接成功")
    # except Exception as e:
    #     logger.critical(f"PostgreSQL数据库连接失败: {str(e)}")
    #     error_window(f"连接PostgreSQL数据库发生异常，请检查网络连接或修改CONFIG.py中的参数\n"
    #                  f"主机地址:{config.POSTGRES_HOST}, 端口:{config.POSTGRES_PORT}\n"
    #                  f"异常信息: {str(e)}", 500, 200)
    #     logger.info("程序退出 - 原因: 数据库连接失败")
    #     return

    # 连接oracle
    # 尝试编辑xcope
    logger.info("测试自动填表功能...")
    try:
        # 使用测试数据测试自动填表功能
        auto_input.xcope.xcope_input(
            xm="测试姓名",
            nl="30",
            zlkh="TEST001",
            ybbh="YB001",
            ch="101",
            bbzl="血液",
            sjys="测试医生",
            sjks="测试科室"
        )
        logger.info("自动填表功能测试成功")
    except Exception as e:
        logger.error(f"自动填表测试失败: {str(e)}")
        error_window(f"自动填表测试失败，请检查系统环境\n"
                     f"异常信息: {str(e)}\n"
                     f"程序将继续运行，但可能无法正常工作", 500, 200)

    # 启动 Xcope 报告轮询线程
    global _XCOPE_POLL_THREAD
    if _XCOPE_POLL_THREAD is None or not _XCOPE_POLL_THREAD.is_alive():
        _XCOPE_POLL_THREAD = threading.Thread(target=_xcope_poll_worker, daemon=True)
        _XCOPE_POLL_THREAD.start()
        logger.info("已启动 Xcope 报告轮询线程")

    # 轮询
    logger.info("进入主循环，等待扫描器输入...")
    try:
        while True:
            try:
                # 获取扫描的内容
                scanner_result = qr_code_scanner.get_scanner_content()
                logger.info(f"扫描器输入: {scanner_result}")

                # 记录最近一次扫描条码，供 Xcope 报告下载命名使用
                _set_last_scanner_code(scanner_result)

                # 检查是否为回退特殊指令
                if scanner_result == "AutoLoaderRollback":
                    current_patient['serial_number'] -= 1
                    logger.info(f"执行回退操作，当前序号变更为: {current_patient['serial_number']}")
                    continue

                # 体检系统条码（不再校验是否以 TJ 开头，任意条码均按体检流程处理）
                logger.info(f"检测到体检系统条码: {scanner_result}")
                # 体检系统的流程
                try:
                    # 体检系统
                    # 生成序列号
                    current_patient['serial_number'] += 1
                    current_time = datetime.datetime.now().strftime("%Y%m%d")
                    serial_number = f"{current_time}S{str(current_patient['serial_number']).zfill(6)}"
                    logger.info(f"生成新序列号: {serial_number}")

                    # 调用东华 MES0201 接口（申请信息列表）获取患者信息
                    # 构造业务请求 XML，请根据医院实际情况调整 SourceSystem/CardTypes/ExeLoc/EpsiodeType
                    request_xml = f"""<Request>
    <Header>
        <SourceSystem>AutoLoader</SourceSystem>
        <MessageID>{serial_number}</MessageID>
    </Header>
    <Body>
        <CardValue>{scanner_result}</CardValue>
        <CardTypes>2</CardTypes>
        <ExeLoc>静秀路放射科</ExeLoc>
        <EpsiodeType>O</EpsiodeType>
    </Body>
</Request>"""

                    his_url = "https://192.168.206.193:1443/csp/hsb/DHC.Published.PISWebService.BS.PISWebService.CLS"
                    form_data = {
                        "input1": "MES0201",  # 服务编码: 申请信息列表
                        "input2": request_xml,  # 业务请求XML
                    }
                    headers = {
                        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
                    }

                    try:
                        response = http_request.get_response(
                            "POST",
                            his_url,
                            1,
                            10,
                            verify=False,
                            headers=headers,
                            data=form_data,
                        )
                    except requests.exceptions.RequestException as e:
                        logger.error(f"调用HIS申请信息列表接口失败: {str(e)}")
                        error_window("获取患者信息失败,请稍后再尝试,错误码:3", 900, 270)
                        continue

                    if response is None:
                        logger.warning("HIS申请信息列表接口无响应或多次重试失败")
                        error_window("获取患者信息失败,请稍后再尝试,错误码:1", 900, 270)
                        continue

                    try:
                        xml_dict = data_processing.xml_to_dict(response.text)
                    except Exception as e:
                        logger.error(f"解析HIS返回XML失败: {str(e)}")
                        error_window("HIS返回数据格式错误，错误码:4", 900, 270)
                        continue

                    body = xml_dict.get("Response", {}).get("Body", {})
                    result_code = str(body.get("ResultCode", "")).strip()
                    if result_code != "0":
                        result_content = body.get("ResultContent", "未知错误")
                        logger.warning(f"HIS接口返回失败: {result_code} {result_content}")
                        error_window(f"HIS接口查询失败: {result_content}", 900, 270)
                        continue

                    pat_ord_lists = body.get("PatOrdLists", {}).get("PatOrdList")
                    if not pat_ord_lists:
                        logger.warning("HIS接口未返回任何申请单信息")
                        error_window("HIS接口未查询到该病人申请信息，错误码:2", 900, 270)
                        continue

                    if isinstance(pat_ord_lists, list):
                        first_order = pat_ord_lists[0]
                    else:
                        first_order = pat_ord_lists

                    xcope_xm = first_order.get("PATName") or ""
                    xcope_nl = first_order.get("PATAge") or ""
                    # 这里优先使用登记号作为诊疗卡号，如有需要可根据医院要求调整
                    xcope_zlkh = first_order.get("PATPatientID") or first_order.get("PAADMVisitNumber") or ""
                    xcope_sjys = first_order.get("RISRSubmitDocDesc") or ""
                    xcope_sjks = first_order.get("AppDeptDesc") or ""
                    xcope_ybbh = f"M{current_time[:4]}{str(current_patient['serial_number']).zfill(5)}"

                    try:
                        auto_input.xcope.xcope_input(
                            xm=xcope_xm,
                            nl=xcope_nl,
                            zlkh=xcope_zlkh,
                            sjys=xcope_sjys,
                            sjks=xcope_sjks,
                            ybbh=xcope_ybbh
                        )
                        logger.info(f"自动填表成功: {xcope_xm}")
                    except FailSafeException:
                        logger.warning("自动填表过程中检测到鼠标移动到屏幕角落")
                        error_window("自动输入过程，鼠标光标请不要移动到屏幕的四个角落，请移动回正确位置再重新扫描。", 900, 300)
                        continue

                except Exception as e:
                    logger.error(f"处理体检系统条码异常: {str(e)}", exc_info=True)
                    error_window(f"处理体检系统条码异常，请重试\n条码: {scanner_result}\n异常信息: {str(e)}", 500, 180)

                # else:
                #     logger.info(f"检测到医院HIS系统条码: {scanner_result}")
                #     # HIS系统的流程
                #     try:
                #         # His系统
                #         # 生成序列号
                #         current_patient['serial_number'] += 1
                #         current_time = datetime.datetime.now().strftime("%Y%m%d")
                #         serial_number = f"{current_time}S{str(current_patient['serial_number']).zfill(6)}"
                #         logger.info(f"生成新序列号: {serial_number}")
                #
                #         # 首先检查表是否存在
                #         check_table_sql = """
                #             SELECT EXISTS (
                #                 SELECT 1
                #                 FROM information_schema.tables
                #                 WHERE table_schema = 'vela_jc'
                #                 AND table_name = 'jc_sq_shenqingdan'
                #             );
                #         """
                #         try:
                #             cursor = pg_conn.cursor()
                #             cursor.execute(check_table_sql)
                #             table_exists = cursor.fetchone()[0]
                #
                #             if not table_exists:
                #                 logger.error("所需的表vela_jc.jc_sq_shenqingdan不存在")
                #                 error_window("数据库缺少必要的表，请联系管理员检查数据库配置", 900, 300)
                #                 cursor.close()
                #                 continue
                #
                #             # 如果表存在，先获取列名
                #             columns_sql = """
                #                 SELECT column_name
                #                 FROM information_schema.columns
                #                 WHERE table_schema = 'vela_jc'
                #                 AND table_name = 'jc_sq_shenqingdan'
                #                 ORDER BY ordinal_position;
                #             """
                #             cursor.execute(columns_sql)
                #             columns = [col[0] for col in cursor.fetchall()]
                #             logger.info(f"表字段名称: {', '.join(columns)}")
                #
                #             # 执行查询
                #             sql = f"""
                #                 SELECT * FROM vela_jc.jc_sq_shenqingdan
                #                 WHERE jiuzhenkh = '{scanner_result}'
                #                 AND zuofeibz = 0  -- 未作废的记录
                #                 ORDER BY chuangjiansj DESC  -- 按创建时间倒序
                #                 LIMIT 1  -- 只取最新的一条
                #             """
                #             cursor.execute(sql)
                #             patient_infos = cursor.fetchall()
                #
                #             # 如果有数据，打印第一条记录的所有字段值
                #             if patient_infos:
                #                 logger.info("查询结果的第一条记录:")
                #                 for idx, col in enumerate(columns):
                #                     logger.info(f"{col}: {patient_infos[0][idx]}")
                #
                #             cursor.close()
                #             # 提交事务
                #             pg_conn.commit()
                #
                #         except Exception as e:
                #             logger.error(f"数据库查询失败: {str(e)}")
                #             error_window(f"数据库查询失败，请检查数据库配置\n异常信息: {str(e)}", 900, 300)
                #             # 回滚事务
                #             pg_conn.rollback()
                #             if cursor and not cursor.closed:
                #                 cursor.close()
                #             continue
                #
                #         length = len(patient_infos)
                #         if length == 1:
                #             patient_info = patient_infos[0]
                #             # 根据实际的字段位置获取数据
                #             xcope_xm = next(patient_info[idx] for idx, col in enumerate(columns) if col == 'xingming')
                #             xcope_nl = next(patient_info[idx] for idx, col in enumerate(columns) if col == 'nianling')
                #             xcope_zlkh = next(patient_info[idx] for idx, col in enumerate(columns) if col == 'jiuzhenkh')
                #             xcope_sjys = next(patient_info[idx] for idx, col in enumerate(columns) if col == 'kaidanrxm')
                #             xcope_sjks = next(patient_info[idx] for idx, col in enumerate(columns) if col == 'kaidanksmc')
                #             xcope_ybbh = f"M{current_time[:4]}{str(current_patient['serial_number']).zfill(5)}"
                #
                #             try:
                #                 auto_input.xcope.xcope_input(
                #                     xm=xcope_xm,
                #                     nl=str(xcope_nl),  # 确保转换为字符串
                #                     zlkh=xcope_zlkh,
                #                     sjys=xcope_sjys,
                #                     sjks=xcope_sjks,
                #                     ybbh=xcope_ybbh
                #                 )
                #                 logger.info(f"自动填表成功: {xcope_xm}")
                #             except FailSafeException:
                #                 logger.warning("自动填表过程中检测到鼠标移动到屏幕角落")
                #                 error_window("自动输入过程，鼠标光标请不要移动到屏幕的四个角落，请移动回正确位置再重新扫描。", 900, 300)
                #                 continue
                #
                #         elif length == 0:
                #             logger.warning(f"未找到患者信息: {scanner_result}")
                #             error_window("该号码在数据库查询不到", 600, 270)
                #             continue
                #         else:
                #             logger.warning(f"找到多个患者记录: {scanner_result}")
                #             error_window("该号码在数据库存在多个,无法自动输入", 600, 270)
                #             continue
                #
                #     except Exception as e:
                #         logger.error(f"处理医院HIS系统条码异常: {str(e)}", exc_info=True)
                #         error_window(f"处理医院HIS系统条码异常，请重试\n条码: {scanner_result}\n异常信息: {str(e)}", 500, 180)

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
        # try:
        #     if 'pg_conn' in locals() and pg_conn:
        #         pg_conn.close()
        #         logger.info("PostgreSQL数据库连接已关闭")
        # except Exception as e:
        #     logger.error(f"关闭数据库连接异常: {str(e)}")
        #
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
