"""工具函数：生成 16 位唯一 MessageID。

约定：
- 返回值为 16 位纯数字字符串；
- 在同一进程内通过自增序号保证在 1 秒内多次调用仍然唯一；
- 格式为: YYYYMMDDHHMMSS + 2 位自增序号。
"""

from __future__ import annotations

from datetime import datetime
import threading

# 生成 MessageID 时使用的线程锁和自增序号
_lock = threading.Lock()
_seq = 0


def generate_message_id() -> str:
    """生成 16 位唯一 MessageID（纯数字）。

    返回示例: "2025011415304501"。
    """
    global _seq

    with _lock:
        # 时间精度到秒，长度 14 位
        prefix = datetime.now().strftime("%Y%m%d%H%M%S")
        # 在同 1 秒内通过 2 位自增序号避免重复，最大支持每秒 100 个请求
        _seq = (_seq + 1) % 100
        return f"{prefix}{_seq:02d}"

