import logging
import os
from logging.handlers import TimedRotatingFileHandler
from core.config import DEBUG_MODE

if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger("rtca_bot")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

file_handler = TimedRotatingFileHandler("logs/bot.log", when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def log_info(msg):
    logger.info(msg)

def log_debug(msg):
    logger.debug(msg)

def log_warn(msg):
    logger.warning(msg)

def log_error(msg):
    logger.error(msg)
