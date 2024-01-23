import json
import logging
import os
from typing import Any, Optional

from github_pr_monitor.constants.app_setting_constants import DEFAULT_CONFIG_FILE_NAME, DEFAULT_CONFIG_DIR, \
    REPO_SEARCH_FILTER_CONFIG_KEY, REFRESH_TIME_CONFIG_KEY


class ConfigManager:

    def __init__(self, dir_name: str = DEFAULT_CONFIG_DIR, file_name: str = DEFAULT_CONFIG_FILE_NAME):
        self.config_path = self._get_config_path(dir_name, file_name)
        self.config = self._load_config()

    def get_repo_search_filter(self) -> str:
        return self._get_config(REPO_SEARCH_FILTER_CONFIG_KEY)

    def set_repo_search_filter(self, repo_search_filter: Optional[str]) -> None:
        self._set_config(REPO_SEARCH_FILTER_CONFIG_KEY, repo_search_filter)

    def get_refresh_time(self) -> int:
        return self._get_config(REFRESH_TIME_CONFIG_KEY)

    def set_refresh_time(self, refresh_time: int):
        self._set_config(REFRESH_TIME_CONFIG_KEY, refresh_time)

    def _get_config(self, key: str) -> Any:
        return self.config.get(key)

    def _set_config(self, key: str, value: Any) -> None:
        self.config[key] = value
        self._save_config()

    def _load_config(self) -> dict[str, Any]:
        try:
            with open(self.config_path, 'r') as config_file:
                return json.load(config_file)
        except FileNotFoundError as e:
            logging.warning(f'Error while loading configuration file: {e}')
            return {}

    def _save_config(self) -> None:
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file)

    @staticmethod
    def _get_config_path(dir_name: str = DEFAULT_CONFIG_DIR, file_name: str = DEFAULT_CONFIG_FILE_NAME) -> str:
        config_dir = os.path.expanduser(dir_name)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return os.path.join(config_dir, file_name)
