from pathlib import Path
import logging


def get_logger(file_path):
    """
    Get logger name after the module folder
    :param file_path: __file__
    :return: logger instance
    """
    module_name = Path(file_path).parent.name
    logger = logging.getLogger(module_name)
    if not logger.handlers:
        handlers = logging.StreamHandler()
        formatter = logging.Formatter(f"[{module_name}] %(levelname)s - %(message)s")
        handlers.setFormatter(formatter)
        logger.addHandler(handlers)
        logger.setLevel(logging.INFO)
    return logger
