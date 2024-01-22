import json
import logging
import os
from typing import Any


class ConfigManager:
    DEFAULT_DIR: str = '~/Library/Application Support/PRMonitor'
    DEFAULT_FILE_NAME: str = 'config.json'
    REPO_SEARCH_FILTER_KEY: str = 'repo_search_filter'
    REFRESH_TIME: str = 'refresh_time'

    def __init__(self, dir_name: str = DEFAULT_DIR, file_name: str = DEFAULT_FILE_NAME):
        self.config_path = self._get_config_path(dir_name, file_name)
        self.config = self._load_config()

    def get_repo_search_filter(self):
        return self._get_config(self.REPO_SEARCH_FILTER_KEY)

    def set_repo_search_filter(self, repo_search_filter: str):
        self._set_config(self.REPO_SEARCH_FILTER_KEY, repo_search_filter)

    def get_refresh_time(self):
        return self._get_config(self.REFRESH_TIME)

    def set_refresh_time(self, refresh_time: int):
        self._set_config(self.REFRESH_TIME, refresh_time)

    def _get_config(self, key: str):
        return self.config.get(key)

    def _set_config(self, key: str, value: Any):
        self.config[key] = value
        self._save_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as config_file:
                return json.load(config_file)
        except FileNotFoundError as e:
            logging.warning(f'Error while loading configuration file: {e}')
            return {}

    def _save_config(self):
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file)

    @staticmethod
    def _get_config_path(dir_name: str = DEFAULT_DIR, file_name: str = DEFAULT_FILE_NAME):
        config_dir = os.path.expanduser(dir_name)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return os.path.join(config_dir, file_name)