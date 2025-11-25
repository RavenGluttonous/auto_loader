"""应用运行配置加载模块

将 config.py 视为运行时外部配置文件（数据文件），
无论是源码运行还是 PyInstaller 打包后的 exe，都通过本模块读取配置。
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from typing import Dict, Any, List

# 默认配置（当找不到 config.py 或解析失败时使用）
_DEFAULTS: Dict[str, Any] = {
    # 串口
    "SERIAL_PORT": "COM1",
    "BAUDRATE": "115200",
    # PostgreSQL（目前代码中已停用，仅作为占位）
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": 5432,
    "POSTGRES_USERNAME": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "POSTGRES_DATABASE": "postgres",
    # Xcope 接口
    "XCOPE_BASE_URL": "http://127.0.0.1:9601",
    "XCOPE_CLIENT_ID": "Xcope_ExternalApi",
    "XCOPE_CLIENT_SECRET": "123456",
    "XCOPE_SCOPE": "Xcope",
}


_config_instance: SimpleNamespace | None = None


def _detect_search_paths(filename: str = "config.py") -> List[str]:
    """根据运行环境推断可能的 config.py 位置（按优先级排序）。

    优先级：
    1. 冻结(exe)时：exe 所在目录
    2. 冻结(exe)时：exe 所在目录的父目录（便于在 dist\auto_loader.exe + 根目录 config.py 场景下使用）
    3. 未冻结时：当前源码目录（app_config.py 所在目录）
    4. PyInstaller 内置数据目录（sys._MEIPASS 内的 config.py）
    """

    search_paths: List[str] = []

    if getattr(sys, "frozen", False):  # 运行于 PyInstaller 打包后的 exe
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        # 1. exe 同目录
        search_paths.append(os.path.join(exe_dir, filename))
        # 2. exe 目录的父目录（例如 dist\auto_loader.exe 与上级源码目录）
        parent_dir = os.path.dirname(exe_dir)
        search_paths.append(os.path.join(parent_dir, filename))
    else:
        # 源码运行：以当前文件所在目录为基准
        base_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths.append(os.path.join(base_dir, filename))

    # 3. PyInstaller 的打包数据目录（--add-data "config.py;.")
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        search_paths.append(os.path.join(meipass, filename))

    # 去重但保持顺序
    unique_paths: List[str] = []
    seen = set()
    for p in search_paths:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)
    return unique_paths


def _load_from_file(path: str) -> Dict[str, Any]:
    """从给定路径加载 config.py，返回其全局命名空间字典（只包含大写变量）。"""
    namespace: Dict[str, Any] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        code = compile(source, path, "exec")
        exec(code, namespace)
    except FileNotFoundError:
        return {}
    except Exception:
        # 为避免循环依赖，这里不引入 logger，简单忽略异常并回退到默认配置
        return {}

    result: Dict[str, Any] = {}
    for key, value in namespace.items():
        if key.isupper():
            result[key] = value
    return result


def load_config() -> SimpleNamespace:
    """加载运行配置并返回 SimpleNamespace 对象。

    - 优先使用外部 config.py（exe 同目录 / 上级目录 / 源码目录）
    - 若找不到或解析失败，则回退到 _DEFAULTS
    - 只暴露大写变量，保持与原 config.py 使用方式一致（config.SERIAL_PORT 等）
    """
    global _config_instance
    if _config_instance is not None:
        return _config_instance

    data: Dict[str, Any] = {}
    for candidate in _detect_search_paths():
        if os.path.isfile(candidate):
            loaded = _load_from_file(candidate)
            if loaded:
                data = loaded
                break

    # 合并默认值
    merged: Dict[str, Any] = dict(_DEFAULTS)
    merged.update(data)

    cfg = SimpleNamespace()
    for key, value in merged.items():
        setattr(cfg, key, value)

    _config_instance = cfg
    return cfg


# 对外暴露与原先类似的 config 对象
config: SimpleNamespace = load_config()

