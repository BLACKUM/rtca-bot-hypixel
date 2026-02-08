from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import hashlib

from core.secrets import DEVELOPER_KEY
from core.logger import log_error, log_info

import os
DYNAMIC_KEY = os.urandom(16)

def get_current_key():
    return DYNAMIC_KEY

def get_current_key_string():
    return base64.b64encode(DYNAMIC_KEY).decode('utf-8')

def decrypt(encrypted_text):
    try:
        key = get_current_key()
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decoded_data = base64.b64decode(encrypted_text)
        padded_data = decryptor.update(decoded_data) + decryptor.finalize()
        
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data.decode('utf-8')
    except Exception as e:
        log_error(f"Decryption failed: {e}")
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
    except:
        return False

def check_developer_key(provided_key):
    return provided_key == DEVELOPER_KEY
