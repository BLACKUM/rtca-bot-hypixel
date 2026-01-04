import logging
import os
import atexit
from queue import Queue
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
from core.config import DEBUG_MODE

if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger("rtca_bot")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

file_handler = TimedRotatingFileHandler("logs/bot.log", when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

log_queue = Queue(-1)
queue_handler = QueueHandler(log_queue)
logger.addHandler(queue_handler)

listener = QueueListener(log_queue, file_handler, console_handler)
listener.start()

atexit.register(listener.stop)

def log_info(msg):
    logger.info(msg)

def log_debug(msg):
    logger.debug(msg)

def log_warn(msg):
    logger.warning(msg)

def log_error(msg):
    logger.error(msg)
