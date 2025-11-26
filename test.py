"""针对 tongling_auto_loader.auto_loader 的基础流程测试。

不修改 auto_loader.py，通过在本文件中构造固定测试数据（条码、报告数据等），
验证以下关键点：
1. 扫码条码会正确进入内部队列，并记录为最后一次扫码内容；
2. _register_document_for_report 会按 Xcope 报告字段组装 RegisterDocument 调用参数；
"""

import base64
import os
import shutil
import tempfile
import unittest

import auto_loader


class FakeRegisterDocumentClient:
    """伪造的 RegisterDocumentClient，仅记录调用参数，不真正调接口。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def register_document(self, **kwargs) -> bool:
        # 记录调用参数，返回 False，避免在测试中删除本地 PDF 文件
        self.calls.append(kwargs)
        return False


class ScannerQueueTests(unittest.TestCase):
    """与扫码队列相关的基础行为测试。"""

    def setUp(self) -> None:
        # 重置队列和“最后一次扫码值”，避免受历史状态影响
        auto_loader._XCOPE_SCANNER_CODE_QUEUE = auto_loader.queue.Queue()
        auto_loader._XCOPE_LAST_SCANNER_CODE = None

    def test_scan_code_enqueued_and_last_code_recorded(self) -> None:
        """调用 _set_last_scanner_code 后，条码应进入队列，并被记录为最后一次扫码。"""

        barcode = "TL00123456"

        # 调用被测方法（模拟扫码枪扫出条码）
        auto_loader._set_last_scanner_code(barcode)

        # 1）队列中应有一条记录
        q = auto_loader._XCOPE_SCANNER_CODE_QUEUE
        self.assertEqual(q.qsize(), 1, "预期扫码队列中有 1 条记录")
        dequeued = q.get_nowait()
        self.assertEqual(dequeued, barcode, "队列中的条码应与扫码内容一致")

        # 2）_XCOPE_LAST_SCANNER_CODE 应记录为该条码
        self.assertEqual(auto_loader._XCOPE_LAST_SCANNER_CODE, barcode)


class RegisterDocumentTests(unittest.TestCase):
    """验证 _register_document_for_report 生成 RegisterDocument 入参是否正确。"""

    def setUp(self) -> None:
        # 为 PDF 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="autoloader_test_")
        # 备份原始的 RegisterDocumentClient 类，测试结束后还原
        self._orig_RegisterDocumentClient = auto_loader.RegisterDocumentClient

    def tearDown(self) -> None:
        auto_loader.RegisterDocumentClient = self._orig_RegisterDocumentClient
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_document_uses_xcope_item_fields(self) -> None:
        """_register_document_for_report 应按 Xcope 报告中的字段组装参数。"""

        # 1）准备伪造的 Xcope 报告 item
        barcode = "TL00998877"
        report_id = "REPORT-XYZ"
        item = {
            "诊疗卡号": "CARD001",
            "姓名": "测试患者",
            "就诊流水号": "VISIT001",
            "样本编号": barcode,
            "医嘱ID": "ORDER001",
        }

        # 2）在临时目录中生成一个简单的 PDF 文件
        pdf_path = os.path.join(self.temp_dir, f"{barcode}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 test content for register_document")

        # 3）使用伪造的 RegisterDocumentClient 调用 _register_document_for_report
        fake_client = FakeRegisterDocumentClient()
        auto_loader._register_document_for_report(
            fake_client,
            report_id=report_id,
            filepath=pdf_path,
            item=item,
            barcode=barcode,
        )

        # 4）断言 RegisterDocument 被调用一次，且关键字段正确
        self.assertEqual(len(fake_client.calls), 1, "预期 RegisterDocument 被调用一次")
        call = fake_client.calls[0]

        # DocumentID 应为报告 Id
        self.assertEqual(call.get("document_id"), report_id)
        # 患者与就诊相关字段应来自 item
        self.assertEqual(call.get("pat_patient_id"), item["诊疗卡号"])
        self.assertEqual(call.get("pat_patient_name"), item["姓名"])
        self.assertEqual(call.get("paadm_visit_number"), item["就诊流水号"])
        # 样本编号 / 条码
        self.assertEqual(call.get("specimen_id"), barcode)
        self.assertEqual(call.get("oeori_order_item_id"), item["医嘱ID"])

        # document_content_base64 应为 PDF 的 Base64 编码（这里只校验能否成功解码且前缀正确）
        document_content_b64 = call.get("document_content_base64")
        self.assertIsInstance(document_content_b64, str)
        # 能被 base64.b64decode 解码说明格式正确
        decoded = base64.b64decode(document_content_b64.encode("utf-8"))
        self.assertTrue(decoded.startswith(b"%PDF-1.4"))


if __name__ == "__main__":
    unittest.main()

