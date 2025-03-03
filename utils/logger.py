"""
AutoLoader日志系统
提供统一的日志记录功能，支持文件轮转和内存优化
"""

import os
import logging
import logging.handlers
import time
from datetime import datetime
from pathlib import Path

# 日志级别常量
LOG_LEVEL_DEBUG = logging.DEBUG
LOG_LEVEL_INFO = logging.INFO
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_ERROR = logging.ERROR
LOG_LEVEL_CRITICAL = logging.CRITICAL

# 全局日志对象
_logger = None

def setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    log_file_prefix="autoloader",
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5,
    console_output=True,
    include_process_id=True,
    include_thread_name=True
):
    """
    初始化日志系统
    
    Args:
        log_level: 日志级别，默认INFO
        log_dir: 日志文件存储目录
        log_file_prefix: 日志文件名前缀
        max_bytes: 单个日志文件最大大小，默认10MB
        backup_count: 保留的日志文件数量
        console_output: 是否同时输出到控制台
        include_process_id: 是否在日志中包含进程ID
        include_thread_name: 是否在日志中包含线程名称
    
    Returns:
        logging.Logger: 配置好的日志记录器对象
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    # 创建日志目录
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 生成日志文件名
    current_date = datetime.now().strftime("%Y%m%d")
    log_filename = f"{log_file_prefix}_{current_date}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # 创建日志记录器
    logger = logging.getLogger("AutoLoader")
    logger.setLevel(log_level)
    
    # 防止日志重复输出
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    
    # 日志格式
    log_format_parts = ['%(asctime)s']
    if include_process_id:
        log_format_parts.append('PID:%(process)d')
    if include_thread_name:
        log_format_parts.append('Thread:%(threadName)s')
    
    log_format_parts.extend([
        '%(levelname)s',
        '%(module)s.%(funcName)s:%(lineno)d',
        '%(message)s'
    ])
    
    log_format = ' | '.join(log_format_parts)
    formatter = logging.Formatter(log_format)
    
    # 创建轮转文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_filepath,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 可选的控制台输出
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 设置为全局日志对象
    _logger = logger
    
    # 记录启动信息
    logger.info(f"===== AutoLoader日志系统启动 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) =====")
    logger.info(f"日志级别: {logging.getLevelName(log_level)}")
    logger.info(f"日志文件: {log_filepath} (最大 {max_bytes/1024/1024:.1f}MB, 保留 {backup_count} 个轮转文件)")
    
    return logger

def get_logger():
    """
    获取全局日志记录器
    
    Returns:
        logging.Logger: 日志记录器对象
    """
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger

def log_function_call(enable=True):
    """
    函数调用日志装饰器，用于记录函数调用、参数、返回值和执行时间
    
    Args:
        enable: 是否启用装饰器功能
    
    Returns:
        函数装饰器
    """
    def decorator(func):
        if not enable:
            return func
        
        def wrapper(*args, **kwargs):
            logger = get_logger()
            start_time = time.time()
            
            # 简化参数日志记录，避免大对象消耗内存
            args_repr = [repr(a) if len(repr(a)) < 100 else f"{type(a).__name__}(长度:{len(repr(a))})" for a in args]
            kwargs_repr = [f"{k}={repr(v) if len(repr(v)) < 100 else f'{type(v).__name__}(长度:{len(repr(v))}'}" for k, v in kwargs.items()]
            args_kwargs_str = ", ".join(args_repr + kwargs_repr)
            
            try:
                logger.debug(f"调用函数 {func.__name__}({args_kwargs_str})")
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录返回值，但避免大对象
                result_repr = repr(result) if result is not None and len(repr(result)) < 100 else f"{type(result).__name__}(长度:{len(repr(result)) if result is not None else 0})"
                logger.debug(f"函数 {func.__name__} 返回: {result_repr} (耗时 {execution_time:.3f}s)")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"函数 {func.__name__} 异常: {str(e)} (耗时 {execution_time:.3f}s)", exc_info=True)
                raise
                
        return wrapper
    return decorator

def memory_check(min_interval=60):
    """
    内存使用情况检查装饰器，用于监控函数执行过程中的内存使用情况
    仅在支持psutil的环境下启用
    
    Args:
        min_interval: 最小检查间隔时间(秒)，避免频繁检查消耗性能
    
    Returns:
        函数装饰器
    """
    # 尝试导入psutil，如果不可用则降级为无操作装饰器
    try:
        import psutil
        HAVE_PSUTIL = True
    except ImportError:
        HAVE_PSUTIL = False
    
    # 记录上次检查时间
    last_check_time = [0]  # 使用列表以便在闭包中修改
    
    def decorator(func):
        if not HAVE_PSUTIL:
            return func
            
        def wrapper(*args, **kwargs):
            # 检查时间间隔
            current_time = time.time()
            if current_time - last_check_time[0] < min_interval:
                return func(*args, **kwargs)
                
            logger = get_logger()
            process = psutil.Process(os.getpid())
            
            # 检查内存使用情况
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            logger.debug(f"函数 {func.__name__} 执行前内存使用: {mem_before:.2f} MB")
            
            result = func(*args, **kwargs)
            
            # 再次检查内存使用情况
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            mem_diff = mem_after - mem_before
            
            # 记录内存使用变化
            if mem_diff > 5:  # 当内存增加超过5MB时，记录警告
                logger.warning(f"函数 {func.__name__} 执行后内存增加显著: {mem_diff:.2f} MB (总共 {mem_after:.2f} MB)")
            else:
                logger.debug(f"函数 {func.__name__} 执行后内存变化: {mem_diff:.2f} MB (总共 {mem_after:.2f} MB)")
                
            # 更新检查时间
            last_check_time[0] = current_time
            
            return result
        return wrapper
    return decorator

# 便捷的日志函数
def debug(msg, *args, **kwargs):
    """记录DEBUG级别日志"""
    get_logger().debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    """记录INFO级别日志"""
    get_logger().info(msg, *args, **kwargs)
    
def warning(msg, *args, **kwargs):
    """记录WARNING级别日志"""
    get_logger().warning(msg, *args, **kwargs)
    
def error(msg, *args, **kwargs):
    """记录ERROR级别日志"""
    get_logger().error(msg, *args, **kwargs)
    
def critical(msg, *args, **kwargs):
    """记录CRITICAL级别日志"""
    get_logger().critical(msg, *args, **kwargs)

def exception(msg, *args, **kwargs):
    """记录异常信息，包含堆栈跟踪"""
    kwargs['exc_info'] = True
    get_logger().error(msg, *args, **kwargs)

# 清理日志文件，保留最近n天的日志
def cleanup_logs(log_dir="logs", days_to_keep=30):
    """
    清理旧的日志文件，仅保留最近指定天数的日志
    
    Args:
        log_dir: 日志文件目录
        days_to_keep: 要保留的天数
    """
    try:
        import glob
        from datetime import datetime, timedelta
        
        logger = get_logger()
        logger.info(f"开始清理日志文件，保留最近 {days_to_keep} 天的日志")
        
        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # 遍历日志文件
        log_pattern = os.path.join(log_dir, "*.log*")
        for log_file in glob.glob(log_pattern):
            try:
                # 从文件名提取日期部分
                filename = os.path.basename(log_file)
                if "_" in filename:
                    date_str = filename.split("_")[1].split(".")[0]
                    if len(date_str) == 8 and date_str.isdigit():
                        file_date = datetime.strptime(date_str, "%Y%m%d")
                        
                        # 检查文件日期是否早于截止日期
                        if file_date < cutoff_date:
                            os.remove(log_file)
                            logger.info(f"已删除过期日志文件: {filename}")
            except Exception as e:
                logger.warning(f"清理日志文件时出错: {str(e)}")
                
        logger.info("日志文件清理完成")
    except Exception as e:
        get_logger().error(f"日志清理失败: {str(e)}") 