from cryptography.fernet import Fernet

from app.providers.security import CredentialCipher


def test_provider_credentials_are_encrypted_and_round_trip():
    cipher = CredentialCipher(Fernet.generate_key().decode())
    plaintext = {"api_key": "secret-key-123", "model": "example-model"}

    encrypted = cipher.encrypt(plaintext)

    assert "secret-key-123" not in encrypted
    assert cipher.decrypt(encrypted) == plaintext
