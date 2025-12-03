import base64
import datetime
import json
import os
import re
import signal
import threading
import time
import sys
import queue

# import psycopg2  # PostgreSQL 已停用，仅保留导入语句供参考
import requests
from pyautogui import FailSafeException

import auto_input.autoscope
import auto_input.xcope
from app_config import config
import scan.scanner
import tray_task.tray_task
from hospital_info import data_processing
from utils import http_request
from utils import logger  # 导入新的日志模块
from xcope_client import XcopeClient
from register_document_client import RegisterDocumentClient
from status_change_client import StatusChangeClient

# Xcope 报告轮询相关全局变量
_XCOPE_CLIENT: XcopeClient | None = None
_XCOPE_POLL_THREAD: threading.Thread | None = None
_XCOPE_POLL_STOP = threading.Event()
_XCOPE_PROCESSED_IDS_LOCK = threading.Lock()
_XCOPE_PROCESSED_IDS: set[str] = set()
_XCOPE_LAST_SCANNER_CODE_LOCK = threading.Lock()
_XCOPE_LAST_SCANNER_CODE: str | None = None

# 扫码队列：按队列、一条码匹配一份新报告，使用线程安全的阻塞队列
_XCOPE_SCANNER_CODE_QUEUE: queue.Queue[str] = queue.Queue()

# 条码与申请单号(RISRAppNum)映射表，用于在保存 PDF 时按申请单号命名
_RISR_APP_NUM_MAP_LOCK = threading.Lock()
_RISR_APP_NUM_MAP: dict[str, str] = {}

# 条码与医嘱明细ID(OEORIOrderItemID) 映射表，用于文档注册和状态变更接口
_OEORI_ORDER_ITEM_ID_MAP_LOCK = threading.Lock()
_OEORI_ORDER_ITEM_ID_MAP: dict[str, str] = {}

# 条码与就诊流水号(PAADMVisitNumber) 映射表，用于文档注册/状态变更接口
_PAADM_VISIT_NUMBER_MAP_LOCK = threading.Lock()
_PAADM_VISIT_NUMBER_MAP: dict[str, str] = {}

# 条码长度控制：正常条码基准长度约为 10 位，超过 1.5 倍认为可能是连续扫码被拼接
_BARCODE_BASE_LENGTH = 10
_BARCODE_MAX_LENGTH = int(_BARCODE_BASE_LENGTH * 1.5)  # 目前为 15

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
    """记录最近一次扫描条码，并放入队列，供 Xcope 轮询按队列精确匹配使用。"""
    global _XCOPE_LAST_SCANNER_CODE
    code = (code or "").strip()
    if not code:
        return
    with _XCOPE_LAST_SCANNER_CODE_LOCK:
        _XCOPE_LAST_SCANNER_CODE = code
    # 使用阻塞队列存放扫码结果；队列为空时，轮询线程会阻塞等待新条码
    try:
        _XCOPE_SCANNER_CODE_QUEUE.put_nowait(code)
    except Exception as e:
        # 理论上不会触发（未设置 maxsize），仅作为健壮性保护
        logger.error(f"将条码加入扫码队列失败: {code}, 错误: {e}")


def _set_risr_app_num_for_barcode(barcode: str, app_num: str) -> None:
    """为给定条码记录对应的申请单号(RISRAppNum)。"""
    barcode = (barcode or "").strip()
    app_num = (app_num or "").strip()
    if not barcode or not app_num:
        return
    with _RISR_APP_NUM_MAP_LOCK:
        _RISR_APP_NUM_MAP[barcode] = app_num


def _get_risr_app_num_for_barcode(barcode: str) -> str | None:
    """根据条码获取对应的申请单号(RISRAppNum)。"""
    barcode = (barcode or "").strip()
    if not barcode:
        return None
    with _RISR_APP_NUM_MAP_LOCK:
        return _RISR_APP_NUM_MAP.get(barcode)


def _set_oeori_order_item_id_for_barcode(barcode: str, order_item_id: str) -> None:
    """为给定条码记录对应的医嘱明细ID(OEORIOrderItemID)。"""
    barcode = (barcode or "").strip()
    order_item_id = (order_item_id or "").strip()
    if not barcode or not order_item_id:
        return
    with _OEORI_ORDER_ITEM_ID_MAP_LOCK:
        _OEORI_ORDER_ITEM_ID_MAP[barcode] = order_item_id


def _get_oeori_order_item_id_for_barcode(barcode: str) -> str | None:
    """根据条码获取对应的医嘱明细ID(OEORIOrderItemID)。"""
    barcode = (barcode or "").strip()
    if not barcode:
        return None
    with _OEORI_ORDER_ITEM_ID_MAP_LOCK:
        return _OEORI_ORDER_ITEM_ID_MAP.get(barcode)


def _set_paadm_visit_number_for_barcode(barcode: str, visit_number: str) -> None:
    """为给定条码记录对应的就诊流水号(PAADMVisitNumber)。"""
    barcode = (barcode or "").strip()
    visit_number = (visit_number or "").strip()
    if not barcode or not visit_number:
        return
    with _PAADM_VISIT_NUMBER_MAP_LOCK:
        _PAADM_VISIT_NUMBER_MAP[barcode] = visit_number


def _get_paadm_visit_number_for_barcode(barcode: str) -> str | None:
    """根据条码获取对应的就诊流水号(PAADMVisitNumber)。"""
    barcode = (barcode or "").strip()
    if not barcode:
        return None
    with _PAADM_VISIT_NUMBER_MAP_LOCK:
        return _PAADM_VISIT_NUMBER_MAP.get(barcode)


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
    """基于阻塞队列的 Xcope 报告轮询线程。

    设计目标：
    - 当有扫码条码进入队列时，线程立即被唤醒，立刻开始尝试匹配并下载报告；
    - 当队列和待处理条码都为空时，线程阻塞等待新条码，不再固定每60秒轮询，避免无效请求；
    - 使用 queue.Queue 保证线程安全，同时通过 timeout 处理队列为空、线程退出等场景，不出现空指针异常。

	    业务规则保持不变：
	    - startDate/EndDate 为当天时间
	    - MaxResultCount 默认 99999
	    - 使用申请单号(RISRAppNum)作为 PDF 文件名（若申请单号缺失则回退为样本编号，再回退为报告 Id），保存到 D:\东华病理报告
	    - 报告和 PDF 根据 report Id 去重
	    - 通过 Xcope 报告中的“样本编号”等字段与扫码条码精确匹配，一条码对应一份新报告
    """
    logger.info("Xcope 报告轮询线程启动")
    client = _ensure_xcope_client()
    if client is None:
        logger.error("XcopeClient 初始化失败，轮询线程退出")
        return

    base_dir = r"D:\\东华病理报告"
    os.makedirs(base_dir, exist_ok=True)

    register_client = RegisterDocumentClient()
    status_client = StatusChangeClient()

    # 挂起在内存中的“待匹配条码”列表：
    # - 新扫码条码会被加入此列表
    # - 若当前轮询未在报告列表中匹配到，将保留在此列表中，等待后续再次轮询
    pending_barcodes: list[str] = []

    # 有待匹配条码时的轮询间隔（秒），避免对 Xcope 接口造成过高压力
    POLL_INTERVAL_SECONDS = 10
    # 从队列中阻塞等待新条码的超时时间（秒），用于定期检查停止事件
    QUEUE_WAIT_TIMEOUT_SECONDS = 1

    while not _XCOPE_POLL_STOP.is_set():
        try:
            # 1. 如果当前没有任何待匹配条码，则阻塞等待队列中出现新条码
            if not pending_barcodes:
                try:
                    barcode_from_queue = _XCOPE_SCANNER_CODE_QUEUE.get(
                        timeout=QUEUE_WAIT_TIMEOUT_SECONDS
                    )
                except queue.Empty:
                    # 队列暂时为空，继续检查停止事件
                    continue

                barcode_from_queue = (barcode_from_queue or "").strip()
                if barcode_from_queue:
                    pending_barcodes.append(barcode_from_queue)
                    logger.info(
                        f"Xcope 轮询线程收到新条码: {barcode_from_queue}（当前待处理共 {len(pending_barcodes)} 条）"
                    )
                # 继续往下执行：立即进行一次轮询
            else:
                # 已经有待匹配条码的情况下，尽量一次性把队列里积压的条码取完
                while True:
                    try:
                        more_code = _XCOPE_SCANNER_CODE_QUEUE.get_nowait()
                    except queue.Empty:
                        break
                    more_code = (more_code or "").strip()
                    if more_code:
                        pending_barcodes.append(more_code)

            if not pending_barcodes:
                # 可能刚刚取到的都是空字符串，直接继续等待
                continue

            # 2. 拉取今日报告列表
            items = client.get_today_report_list(max_result_count=99999)
            logger.info(f"Xcope 今日报告总数: {len(items)}")

            # 预先过滤出未处理的报告，并缓存 report_id 方便后续使用
            unprocessed_items: list[dict] = []
            for item in items:
                report_id = str(item.get("Id") or "").strip()
                if not report_id:
                    continue
                if _is_report_processed(report_id):
                    continue
                # 临时附加 report_id，便于后续使用
                item["_report_id"] = report_id
                unprocessed_items.append(item)

            if not unprocessed_items:
                # 当前没有任何尚未处理的报告：如果还有待匹配条码，稍后再重试；否则直接返回顶部阻塞等待新条码
                if pending_barcodes:
                    time.sleep(POLL_INTERVAL_SECONDS)
                continue

            # 本轮需要反馈的平台文档信息列表（去重后），以及成功匹配的条码列表
            to_register: list[dict] = []
            matched_barcodes: list[str] = []

            def _extract_sample_code(report_item: dict) -> str:
                """从 Xcope 报告中提取用于精确匹配条码的样本编号/标本编号等字段。"""
                for key in ("样本编号", "标本编号", "样本号", "标本号"):
                    value = str(report_item.get(key) or "").strip()
                    if value:
                        return value
                return ""

            # 3. 按 pending_barcodes 顺序，一条码精确匹配一份未处理报告
            for barcode in list(pending_barcodes):
                barcode = (barcode or "").strip()
                if not barcode:
                    continue

                matched_index: int | None = None
                for idx, report_item in enumerate(unprocessed_items):
                    sample_code = _extract_sample_code(report_item)
                    if sample_code and sample_code == barcode:
                        matched_index = idx
                        break

	                # 当前条码暂未在报告列表中找到匹配项，保留在 pending_barcodes 中，等待后续轮询
                if matched_index is None:
                    continue
	
                matched_item = unprocessed_items.pop(matched_index)
                report_id = matched_item.get("_report_id") or ""
                report_id = str(report_id).strip()
                if not report_id:
                    logger.warning(f"匹配到的 Xcope 报告缺少 Id 字段，条码={barcode}")
                    continue

                # 优先使用申请信息列表接口返回的申请单号(RISRAppNum)作为 PDF 文件名；
                # 如未能获取申请单号，则回退为样本编号，再回退为报告 Id
                app_num_for_filename = _get_risr_app_num_for_barcode(barcode)
                if app_num_for_filename:
                    filename_base = app_num_for_filename
                else:
                    sample_code_for_filename = _extract_sample_code(matched_item) or report_id
                    filename_base = sample_code_for_filename

                pdf_bytes = client.download_report_pdf(report_id)
                if not pdf_bytes:
                    logger.warning(f"下载 Xcope 报告 PDF 失败，报告Id={report_id}，条码={barcode}")
                    continue

                filename = f"{filename_base}.pdf"
                filepath = os.path.join(base_dir, filename)

                try:
                    with open(filepath, "wb") as f:
                        f.write(pdf_bytes)
                    logger.info(f"已保存 Xcope 报告 PDF: {filepath}，条码={barcode}")
                    _mark_report_processed(report_id)

                    to_register.append(
                        {
                            "report_id": report_id,
                            "filepath": filepath,
                            "item": matched_item,
                            "barcode": barcode,
                        }
                    )
                    matched_barcodes.append(barcode)
                except Exception as e:
                    logger.error(f"保存 Xcope 报告 PDF 失败: {filepath}，条码={barcode}，错误: {e}")

            # 4. 当列表数据全部操作完后，再调用反馈接口
            for info in to_register:
                _register_document_for_report(
                    register_client,
                    status_client,
                    info["report_id"],
                    info["filepath"],
                    info["item"],
                    info["barcode"],
                )

            # 5. 从 pending_barcodes 中移除已成功匹配并处理的条码（按出现次数移除，支持重复扫码场景）
            if matched_barcodes:
                remove_counts: dict[str, int] = {}
                for c in matched_barcodes:
                    c = (c or "").strip()
                    if not c:
                        continue
                    remove_counts[c] = remove_counts.get(c, 0) + 1

                if remove_counts:
                    new_pending: list[str] = []
                    for c in pending_barcodes:
                        count = remove_counts.get(c, 0)
                        if count > 0:
                            # 消耗一次该条码
                            remove_counts[c] = count - 1
                            continue
                        new_pending.append(c)
                    pending_barcodes = new_pending

            # 6. 如果还有未匹配成功的条码，等待一小段时间后再次轮询；否则回到顶部阻塞等待新条码
            if pending_barcodes:
                time.sleep(POLL_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"Xcope 报告轮询线程异常: {e}", exc_info=True)
            # 出现异常时适当休眠，避免异常情况下的忙等
            time.sleep(POLL_INTERVAL_SECONDS)



def _register_document_for_report(
    register_client: RegisterDocumentClient,
    status_client: StatusChangeClient,
    report_id: str,
    filepath: str,
    item: dict,
    barcode: str,
) -> None:
    """将单条报告使用 RegisterDocument 反馈给医院平台，并在成功后回传状态变更(MES0167)。

    当前实现：
    - 使用 Xcope 报告 Id 作为 DocumentID
    - DocumentPath 使用固定前缀 + PDF 文件名，例如：
      http://192.168.206.174/blk/pathology/report/202509055.pdf
    - 其他字段从 item 中尽量提取，如获取不到则置空
    - 文档注册成功后，调用 MES0167 状态变更回传接口，上报状态代码 RP（报告完成）
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

        # 从 Xcope 报告 item / 华东申请列表 中尽量提取患者及就诊信息（字段名为中文，示例中采用常见字段名）
        # 这里保留从报告中取出的登记号/诊疗卡号，用于后续状态变更(MES0167) 上报
        his_pat_patient_id = str(item.get("诊疗卡号") or "")
        pat_patient_name = str(item.get("姓名") or "")
        # PAADMVisitNumber 优先从华东申请列表(MES0201) 的映射中获取，
        # 若未命中映射，则回退使用 Xcope 报告中可能携带的就诊流水号/PAADMVisitNumber 字段
        paadm_visit_number = (
            _get_paadm_visit_number_for_barcode(barcode)
            or str(item.get("就诊流水号") or item.get("PAADMVisitNumber") or "")
        )
        specimen_id = str(item.get("样本编号") or "")
        # 优先使用申请信息列表(MES0201) 中保存的 OEORIOrderItemID；
        # 若未找到，则回退使用 Xcope 报告中可能携带的 OEORIOrderItemID/医嘱ID 字段
        oeori_order_item_id = (
            _get_oeori_order_item_id_for_barcode(barcode)
            or str(item.get("OEORIOrderItemID") or item.get("医嘱ID") or "")
        )

        # 文档注册接口要求：PATPatientID 传入扫码枪扫描到的条码
        # 若异常情况下条码为空，则回退使用报告中的登记号/诊疗卡号
        pat_patient_id_for_register = (barcode or "").strip() or his_pat_patient_id

        # 如果 Xcope 返回中没有上述字段，可以根据实际字段名调整

        # DocumentPath 按医院要求：固定前缀 + PDF 文件名
        # 例如：http://192.168.206.174/blk/pathology/report/202509055.pdf
        filename_only = os.path.basename(filepath)
        base_url = "http://192.168.206.174/blk/pathology/report/"
        if filename_only:
            document_path = base_url.rstrip("/") + "/" + filename_only
        else:
            # 异常情况下退回使用前缀本身
            document_path = base_url.rstrip("/")

        success = register_client.register_document(
            message_id=message_id,
            organization_code="0001",
            # 文档注册 PATPatientID 使用扫码条码
            pat_patient_id=pat_patient_id_for_register,
            pat_patient_name=pat_patient_name,
            paadm_visit_number=paadm_visit_number,
            specimen_id=specimen_id,
            oeori_order_item_id=oeori_order_item_id,
            document_type="02006",  # 病理报告
            # 文档注册 DocumentID 按要求传申请列表中的 PAADMVisitNumber（就诊流水号）
            document_id=paadm_visit_number,
            document_content_base64=document_content_base64,
            document_path=document_path,
            document_pic_path="",  # 如有需要可根据实际情况填写
            update_user_code="AutoLoader",
            update_date=update_date,
            update_time=update_time,
        )

        if success:
            logger.info(f"文档注册成功，报告Id={report_id}，条码={barcode}")

            # 文档注册成功后，按病理闭环要求回传状态变更（MES0167），状态代码示例使用 RP（报告完成）
            status_message_id = f"STS-{now.strftime('%Y%m%d%H%M%S')}-{report_id}"
            update_datetime = now.strftime("%Y-%m-%d %H:%M:%S")

            # 尝试从 Xcope 报告中获取检查号等字段，如无对应字段可按实际医院字段名调整
            risr_exam_id = str(
                item.get("检查号")
                or item.get("RISRExamID")
                or item.get("申请单号")
                or ""
            )

            # 从配置文件中获取状态变更的更新人信息（UpdateUserCode/UpdateUserName）
            update_user_code = "AutoLoader"
            update_user_name = "AutoLoader"
            try:
                users_cfg = getattr(config, "STATUS_UPDATE_USERS", None)
                if isinstance(users_cfg, list) and users_cfg:
                    first_user = users_cfg[0]
                    if isinstance(first_user, dict):
                        update_user_code = str(
                            first_user.get("UpdateUserCode", update_user_code)
                        )
                        update_user_name = str(
                            first_user.get("UpdateUserName", update_user_name)
                        )
            except Exception:
                # 配置异常时回退到默认值，避免中断闭环逻辑
                pass

            status_param = {
                # 状态变更 PATPatientID 也改为扫码条码，异常时回退登记号/诊疗卡号
                "PATPatientID": pat_patient_id_for_register,
                "PAADMVisitNumber": paadm_visit_number,
                "OEORIOrderItemID": oeori_order_item_id,
                "OEORIOrdExecID": "",
                "SpecimenID": specimen_id,
                "RISRExamID": risr_exam_id,
                "RISRSystemType": "PIS",  # 病理系统类型，具体取值可按医院附录配置调整
                "Position": "",
                "OperAppID": "",
                "BloodAppID": "",
                "BloodBagNo": "",
                "ConsultAppID": "",
                "StatusCode": "RP",  # 报告完成
                "UpdateUserCode": update_user_code,
                "UpdateUserName": update_user_name,
                "UpdateDateTime": update_datetime,
                "ESOperateDeptCode": "",
                "ESOperateDept": "",
                "ESReportID": "",
            }

            try:
                status_success = status_client.send_status_change(
                    message_id=status_message_id,
                    source_system="02",
                    status_params=[status_param],
                )
                if status_success:
                    logger.info(
                        f"状态变更回传成功(MES0167)，报告Id={report_id}，条码={barcode}，状态代码=RP"
                    )
                else:
                    logger.error(
                        f"状态变更回传失败(MES0167)，报告Id={report_id}，条码={barcode}，状态代码=RP"
                    )
            except Exception as e:
                logger.error(
                    f"状态变更回传过程中发生异常(MES0167)，报告Id={report_id}，条码={barcode}，错误: {e}",
                    exc_info=True,
                )

            # 注册及状态回传逻辑完成后，删除本地PDF文件，避免磁盘堆积
            try:
                os.remove(filepath)
                logger.info(f"已删除本地PDF文件: {filepath}")
            except OSError as oe:
                logger.warning(f"删除本地PDF文件失败: {filepath}，错误: {oe}")
        else:
            logger.error(f"文档注册失败，报告Id={report_id}，条码={barcode}")

    except Exception as e:
        logger.error(
            f"文档注册过程中发生异常，报告Id={report_id}，条码={barcode}，错误: {e}",
            exc_info=True,
        )

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
                scanner_result_raw = qr_code_scanner.get_scanner_content()
                logger.info(f"扫描器输入: {scanner_result_raw!r}")

                # 标准化扫描结果（去掉首尾空白/换行）
                scanner_result = (scanner_result_raw or "").strip()
                if not scanner_result:
                    logger.warning("扫描器返回空内容，本次扫描将被忽略")
                    continue

                # 检查是否为回退特殊指令（不作为条码入队）
                if scanner_result == "AutoLoaderRollback":
                    current_patient['serial_number'] -= 1
                    logger.info(f"执行回退操作，当前序号变更为: {current_patient['serial_number']}")
                    continue

                # 长度校验：长度过长时认为是连续扫码导致的拼接，提示用户重新扫码，并丢弃本次结果
                if len(scanner_result) >= _BARCODE_MAX_LENGTH:
                    logger.warning(
                        f"检测到疑似连续扫码导致的异常条码，长度={len(scanner_result)}，内容={scanner_result!r}，本次将丢弃"
                    )
                    error_window(
                        "扫码速度过快，检测到条码长度异常。\n\n"
                        "请稍后重新扫码，注意两次扫码之间留出一点时间。",
                        900,
                        270,
                    )
                    continue

                # 记录最近一次扫描条码，供 Xcope 报告下载命名和轮询使用
                _set_last_scanner_code(scanner_result)

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
                    # 按对方在 SoapUI 中通过测试的示例，先构造内部业务 XML，再封装到 SOAP Envelope 中
                    request_xml = f"""<Request>
    <Header>
        <SourceSystem>RuiKe</SourceSystem>
        <MessageID>{serial_number}</MessageID>
    </Header>
    <Body>
        <CardValue>{scanner_result}</CardValue>
        <CardTypes>2</CardTypes>
        <ExeLoc>静秀路病理科</ExeLoc>
        <EpsiodeType>I</EpsiodeType>
    </Body>
</Request>"""

                    # SOAP 1.1 Envelope，请求体结构与对方 SoapUI 示例保持一致
                    soap_envelope = f"""<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dhcc=\"http://www.dhcc.com.cn\">
   <soapenv:Header/>
   <soapenv:Body>
      <dhcc:HIPMessageServer>
         <dhcc:input1>MES0201</dhcc:input1>
         <dhcc:input2><![CDATA[{request_xml}]]></dhcc:input2>
      </dhcc:HIPMessageServer>
   </soapenv:Body>
</soapenv:Envelope>"""

                    his_url = "https://192.168.206.193:1443/csp/hsb/DHC.Published.PISWebService.BS.PISWebService.CLS"
                    headers = {
                        "Content-Type": "text/xml; charset=utf-8",
                        # 按照 SOAP 1.1 规范和对方 WSDL 约定，补充 SOAPAction 头；
                        # 典型写法为 "http://www.dhcc.com.cn/HIPMessageServer"，两侧带引号与 SoapUI 一致
                        "SOAPAction": "\"http://www.dhcc.com.cn/HIPMessageServer\"",
                    }

                    try:
                        response = http_request.get_response(
                            "POST",
                            his_url,
                            1,
                            3,
                            verify=False,
                            headers=headers,
                            data=soap_envelope,
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
                        # 记录 HIS 申请信息列表接口的原始响应内容，便于对比返回体数据格式
                        raw_xml = response.text or ""
                        if len(raw_xml) > 2000:
                            log_xml = raw_xml[:2000] + "...(已截断)"
                        else:
                            log_xml = raw_xml
                        logger.info(f"HIS申请信息列表接口原始响应: {log_xml}")
                    except Exception as e:
                        # 打印原始响应不影响后续解析，异常仅记录日志
                        logger.warning(f"记录HIS原始响应内容时发生异常: {e}")

                    try:
                        response_node = data_processing.parse_dhcc_hip_response(response.text)
                    except Exception as e:
                        logger.error(f"解析HIS返回XML失败: {str(e)}")
                        error_window("HIS返回数据格式错误，错误码:4", 900, 270)
                        continue

                    if not response_node:
                        logger.error("HIS返回数据格式错误：未能解析到<Response>节点")
                        error_window("HIS返回数据格式错误，错误码:4", 900, 270)
                        continue

                    body = response_node.get("Body", {})
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

                    # 记录当前条码对应的申请单号(RISRAppNum)
                    app_num = str(first_order.get("RISRAppNum") or "").strip()
                    if app_num:
                        _set_risr_app_num_for_barcode(scanner_result, app_num)

                    # 记录当前条码对应的医嘱明细ID(OEORIOrderItemID)
                    order_item_id = str(first_order.get("OEORIOrderItemID") or "").strip()
                    if order_item_id:
                        _set_oeori_order_item_id_for_barcode(scanner_result, order_item_id)

                    # 记录当前条码对应的就诊流水号(PAADMVisitNumber)
                    visit_number = str(first_order.get("PAADMVisitNumber") or "").strip()
                    if visit_number:
                        _set_paadm_visit_number_for_barcode(scanner_result, visit_number)

                    xcope_xm = first_order.get("PATName") or ""
                    xcope_nl = first_order.get("PATAge") or ""
                    # 这里优先使用登记号作为诊疗卡号，如有需要可根据医院要求调整
                    xcope_zlkh = first_order.get("RISRAppNum") or first_order.get("PAADMVisitNumber") or ""
                    xcope_sjys = first_order.get("RISRSubmitDocDesc") or ""
                    xcope_sjks = first_order.get("AppDeptDesc") or ""
                    # 样本编号改为使用扫码枪获取的条码
                    xcope_ybbh = scanner_result

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
        # 关闭扫描器连接
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
