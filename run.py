#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AutoLoader 程序入口
"""
import argparse
import os
import sys
import time

from utils import logger

# 初始化日志系统
logger.setup_logging(
    log_level=logger.LOG_LEVEL_INFO,
    log_file_prefix="autoloader_run",
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5
)

@logger.log_function_call()
def main():
    """
    程序主入口
    """
    parser = argparse.ArgumentParser(description='AutoLoader 程序运行工具')
    parser.add_argument('--dev', action='store_true', help='使用开发环境配置运行')
    args = parser.parse_args()

    # 记录基本环境信息
    logger.info("===== AutoLoader 程序启动 =====")
    logger.info(f"操作系统: {sys.platform}")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")

    if args.dev:
        logger.info("使用开发环境配置启动")
        try:
            from auto_loader_dev import main as dev_main
            logger.info("已导入开发环境主程序")
            dev_main()
        except Exception as e:
            logger.critical(f"开发环境启动失败: {str(e)}", exc_info=True)
            print(f"开发环境启动失败: {str(e)}")
            sys.exit(1)
    else:
        logger.info("使用生产环境配置启动")
        try:
            from auto_loader import main as prod_main
            logger.info("已导入生产环境主程序")
            prod_main()
        except Exception as e:
            logger.critical(f"生产环境启动失败: {str(e)}", exc_info=True)
            print(f"生产环境启动失败: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    try:
        # 尝试清理过期日志文件（保留30天）
        logger.cleanup_logs(days_to_keep=30)
    except Exception as e:
        print(f"清理日志文件失败: {str(e)}")
        
    try:
        main()
    except KeyboardInterrupt:
        logger.info("检测到键盘中断，程序正常退出")
        print("\n程序已被用户中断")
    except Exception as e:
        logger.critical(f"程序异常退出: {str(e)}", exc_info=True)
        print(f"\n程序异常退出: {str(e)}")
    finally:
        logger.info("===== AutoLoader 程序结束 =====") 