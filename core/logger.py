from core.config import DEBUG_MODE


def log_info(msg):
    print(f"[INFO] {msg}")


def log_debug(msg):
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")


def log_warn(msg):
    print(f"[WARN] {msg}")


def log_error(msg):
    print(f"[ERROR] {msg}")
