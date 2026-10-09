"""日志配置。"""

import logging


def configure_logging():
    """配置根日志记录器为 INFO 级别并设置统一格式。"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
