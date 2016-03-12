import logging
import os
import config
import datetime


def setup_logging():
    if not os.path.exists(config.log_path):
        os.makedirs(config.log_path)
    log_file_name = datetime.datetime.now().strftime("client_%Y-%m-%d_%H-%M-%S")

    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("{0}/{1}.log".format(config.log_path, log_file_name))
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


print_info = logging.info
print_warning = logging.warning
print_debug = logging.debug
print_error = logging.error
