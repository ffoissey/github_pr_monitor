import keyring


class KeyringManager:

    _GITHUB_SERVICE_NAME: str = 'github'
    _TOKEN_KEY: str = 'token'

    def __init__(self):
        self._github_pat = self._load_github_pat()

    def set_github_pat(self, token: str) -> None:
        keyring.set_password(self._GITHUB_SERVICE_NAME, self._TOKEN_KEY, token if token != '' else None)
        self._github_pat = token

    def get_github_pat(self) -> str:
        return self._github_pat

    def _load_github_pat(self) -> str:
        token = keyring.get_password(self._GITHUB_SERVICE_NAME, self._TOKEN_KEY)
        return token if token != '' else None

