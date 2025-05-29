import hashlib
import uos
from cryptolib import aes

class Crypto:
    def __init__(self, passphrase):
        # Crear clave sha256 de 32 bytes
        self.key = hashlib.sha256(passphrase.encode('utf-8')).digest()
        self.mode = 2  # AES.MODE_CBC

    def pad(self, data):
        pad_len = 16 - (len(data) % 16)
        return data + bytes([pad_len] * pad_len)

    def unpad(self, data):
        pad_len = data[-1]
        return data[:-pad_len]

    def encrypt(self, plaintext):
        # plaintext es str, pasar a bytes
        data = plaintext.encode('utf-8')
        padded = self.pad(data)
        iv = uos.urandom(16)
        cipher = aes(self.key, self.mode, iv)
        encrypted = cipher.encrypt(padded)
        return iv + encrypted  # concatenar IV + mensaje cifrado

    def decrypt(self, encrypted):
        # encrypted es bytes (IV + ciphertext)
        iv = encrypted[:16]
        ciphertext = encrypted[16:]
        cipher = aes(self.key, self.mode, iv)
        padded = cipher.decrypt(ciphertext)
        data = self.unpad(padded)
        return data.decode('utf-8')