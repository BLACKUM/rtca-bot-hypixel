from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import os
import time
import threading

from core.secrets import DEVELOPER_KEY
from core.logger import log_error, log_info

KEY_GRACE_SECONDS = 300

_lock = threading.Lock()
_active_keys: list = []


def _generate_key() -> bytes:
    return os.urandom(16)


def _ensure_initialized() -> None:
    with _lock:
        if not _active_keys:
            _active_keys.append((_generate_key(), None))


def _purge_expired_locked(now: float) -> None:
    _active_keys[:] = [(k, exp) for (k, exp) in _active_keys if exp is None or exp > now]


def get_current_key() -> bytes:
    _ensure_initialized()
    with _lock:
        return _active_keys[0][0]


def get_current_key_string() -> str:
    return base64.b64encode(get_current_key()).decode('utf-8')


def rotate_key() -> str:
    _ensure_initialized()
    now = time.time()
    new_key = _generate_key()
    with _lock:
        prev_key, _ = _active_keys[0]
        _active_keys[0] = (prev_key, now + KEY_GRACE_SECONDS)
        _active_keys.insert(0, (new_key, None))
        _purge_expired_locked(now)
        active_count = len(_active_keys)
    log_info(f"[Security] Key rotated. Previous key valid for {KEY_GRACE_SECONDS}s. Active keys: {active_count}")
    return base64.b64encode(new_key).decode('utf-8')


def _all_active_keys() -> list:
    _ensure_initialized()
    now = time.time()
    with _lock:
        _purge_expired_locked(now)
        return [k for (k, _exp) in _active_keys]


def _try_decrypt_with_key(decoded_data: bytes, key: bytes):
    if len(decoded_data) < 16:
        return None
    try:
        iv = decoded_data[:16]
        ciphertext = decoded_data[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data.decode('utf-8')
    except Exception:
        pass
    try:
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(decoded_data) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data.decode('utf-8')
    except Exception:
        return None


def decrypt(encrypted_text):
    if not encrypted_text:
        return None
    try:
        decoded_data = base64.b64decode(encrypted_text)
    except Exception as e:
        log_error(f"Decryption failed: invalid base64 ({e})")
        return None

    for key in _all_active_keys():
        result = _try_decrypt_with_key(decoded_data, key)
        if result is not None:
            return result

    log_error("Decryption failed: no active key matches (mod likely needs to refetch /v1/key)")
    return None


def verify_identity(encrypted_identity, claimed_uuid):
    if not encrypted_identity:
        return False

    decrypted = decrypt(encrypted_identity)
    if not decrypted:
        return False

    try:
        parts = decrypted.split(':')
        if len(parts) < 3:
            return False

        decrypted_uuid = parts[0].replace('-', '')
        claimed_uuid = claimed_uuid.replace('-', '')

        return decrypted_uuid == claimed_uuid
    except Exception:
        return False


def check_developer_key(provided_key):
    return provided_key == DEVELOPER_KEY
