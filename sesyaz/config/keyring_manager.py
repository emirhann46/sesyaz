import keyring
import keyring.errors

SERVICE = "sesyaz"
USER = "openai_api_key"


class KeyringManager:
    @staticmethod
    def get_key() -> str | None:
        try:
            return keyring.get_password(SERVICE, USER)
        except keyring.errors.KeyringError:
            return None

    @staticmethod
    def set_key(api_key: str):
        keyring.set_password(SERVICE, USER, api_key)

    @staticmethod
    def delete_key():
        try:
            keyring.delete_password(SERVICE, USER)
        except keyring.errors.PasswordDeleteError:
            pass

    @staticmethod
    def has_key() -> bool:
        return bool(KeyringManager.get_key())
