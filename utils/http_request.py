import logging
import time

import requests
from requests import RequestException, Response

# 使用新的日志模块
from utils import logger

def get_response(method: str, url: str, retry_interval: list[int] | int = -1,
                 retry_number: int = 1, **kwargs) -> Response | None:
    """
    通过requests获取响应信息，具有设置自定义间隔时间
    Args:
        method: 支持 GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD 方法
        url: url
        retry_interval: list[int] 时间间隔列表，单位为秒，依次执行 list 里面的时间， int 为固定间隔时间(尝试次数由 retry_number 决定),
            值为 0 进行无限尝试,值为 -1 采取默认间隔:[30, 60, 120, 180, 240, 300, 600, 1200, 1800, 3600]
        retry_number: 重试次数的总数，只有 retry_interval 是 int 时才生效
        **kwargs: requests的所有参数

    Returns:
        返回 None 代表失败，成功返回 Response
    """
    # 记录请求信息
    logger.info(f"HTTP请求: {method} {url}")
    
    if retry_interval == -1:
        retry_interval = [30, 60, 120, 180, 240, 300, 600, 1200, 1800, 3600]
    result: Response | None = None
    if isinstance(retry_interval, list):
        # 循环次数
        retry_number = len(retry_interval)
        for i in range(retry_number):
            result = _delivery_request(
                method, url, retry_interval[i], i + 1, **kwargs)
            if result is not None:
                break
    elif isinstance(retry_interval, int):
        if retry_number != 0:
            for i in range(retry_number):
                result = _delivery_request(
                    method, url, retry_interval, i + 1, **kwargs)
                if result is not None:
                    break
        else:
            while True:
                result = _delivery_request(
                    method, url, retry_interval, **kwargs)
                if result is not None:
                    break
    
    # 记录请求结果
    if result is not None:
        logger.info(f"HTTP请求成功: {method} {url} (状态码: {result.status_code})")
    else:
        logger.error(f"HTTP请求最终失败: {method} {url} (已重试完所有次数)")
        
    return result


@logger.log_function_call(enable=True)  # 使用函数调用日志装饰器
def _delivery_request(
        method: str, url: str, sleep_time: int, fail_number: int = -1, **kwargs) -> Response | None:
    """
        对url进行发送请求，失败就执行睡眠和输出失败相关信息
        Args:
            method: 支持 GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD 方法
            url: url
            sleep_time: 睡眠时间，单位为秒
            fail_number: 失败时输出的编号,值为-1为不输出编号
            **kwargs: requests的所有参数
        Returns:
            返回 None 代表失败，成功返回 Response
        """
    try:
        # 记录详细请求信息(DEBUG级别)
        if kwargs.get('data'):
            data_str = str(kwargs['data'])
            if len(data_str) > 500:
                data_str = data_str[:500] + "...(已截断)"
            logger.debug(f"HTTP请求数据: {method} {url} data={data_str}")
            
        if kwargs.get('json'):
            json_str = str(kwargs['json'])
            if len(json_str) > 500:
                json_str = json_str[:500] + "...(已截断)"
            logger.debug(f"HTTP请求JSON: {method} {url} json={json_str}")
            
        response: Response = requests.request(method, url, **kwargs)
    except RequestException as e:
        if fail_number != -1:
            logger.warning(
                f"向 {url} 发送{method}请求发生异常,失败次数: {fail_number},休息 {sleep_time} 秒,异常为: {str(e)}")
        else:
            logger.warning(f"向 {url} 发送{method}请求发生异常,休息 {sleep_time} 秒,异常为: {str(e)}")
        
        # 记录详细异常信息
        logger.exception(f"HTTP请求异常详情: {method} {url}")
        
        time.sleep(sleep_time)
        return None
    
    if response.status_code == requests.codes.ok:
        # 可选：记录响应内容(仅DEBUG级别)
        try:
            content_str = response.text
            if len(content_str) > 1000:
                content_str = content_str[:1000] + "...(已截断)"
            logger.debug(f"HTTP响应内容: {method} {url} - {content_str}")
        except Exception as e:
            logger.debug(f"无法记录HTTP响应内容: {str(e)}")
            
        return response
    else:
        if fail_number != -1:
            logger.warning(
                f"向 {url} 发送{method}请求发生异常HTTP状态码,失败次数: {fail_number},休息 {sleep_time} 秒,HTTP状态码:"
                f" {response.status_code},状态码原因: {response.reason}")
        else:
            logger.warning(
                f"向 {url} 发送{method}请求发生异常,休息 {sleep_time} 秒,HTTP状态码: {response.status_code},状态码原因:{response.reason}")
        
        # 记录响应内容(异常情况下)
        try:
            error_content = response.text
            if len(error_content) > 500:
                error_content = error_content[:500] + "...(已截断)"
            logger.warning(f"HTTP错误响应内容: {error_content}")
        except Exception:
            pass
            
        time.sleep(sleep_time)
    return None