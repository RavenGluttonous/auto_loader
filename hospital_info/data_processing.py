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
    """
    将xml格式的字符串转换为dict
    Args:
        xml_data: xml格式的字符串

    Returns:
        dict
    """
    data = xmltodict.parse(xml_data, process_namespaces=True)
    return data
