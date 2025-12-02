import json
import re

import xmltodict


def auto_text_to_dict(text: str, content_type) -> dict | None:
    """
    自动把字符串的内容转换为dict，目前只支持application/json, application/xml
    Args:
        text: 需要转换的字符串
        content_type: 内容类型

    Returns:
        dict
    """
    type_result = _check_content_type(content_type)
    if type_result is None:
        return None
    if type_result == "application/json":
        data = json_to_dict(text)
        return data
    elif type_result == "application/xml":
        data = xml_to_dict(text)
        return data


def _check_content_type(content_type: str) -> str | None:
    """
    检测content_type里面的MIME类型是否在支持的检测范围内，检测列表：[application/json, application/xml]
    Args:
        content_type:内容类型的字符串

    Returns:
        返回检测到的内容类型
    """
    mime_types = ["application/json", "application/xml"]
    result=None
    for mime_type in mime_types:
        result = re.match(mime_type, content_type)
        if result:
            break
    if result is None:
        return None
    return result.group()


def json_to_dict(json_data: str) -> dict:
    """
    将json格式的字符串转换为dict
    Args:
        json_data: json格式的字符串

    Returns:
        dict
    """
    data = json.loads(json_data)
    return data


def xml_to_dict(xml_data: str) -> dict:
    """将 XML 格式的字符串转换为 dict。

    说明：
    - 这里不再启用 ``process_namespaces=True``，避免默认命名空间或前缀
      导致标签名被替换为 ``{namespace}Response`` 之类，
      影响后续通过 "Response"/"Body"/"ResultCode" 等简单键访问。
    - 对于本项目对接的东华 HIS / PIS 接口，业务方文档与示例均以
      无命名空间前缀的标签名为准，因此忽略命名空间更符合使用习惯。
    """
    # 不处理命名空间，直接使用原始标签名作为 key，便于按文档中的字段名取值
    data = xmltodict.parse(xml_data)
    return data
