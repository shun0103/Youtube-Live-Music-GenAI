"""
設定の読み込みと管理を行うモジュール
"""
import json
import os
from typing import Dict, Any, Optional

class ConfigManager:
    """設定を管理するクラス"""
    
    _instance = None
    _config = None
    
    def __new__(cls, config_file: str = None):
        """シングルトンパターンを実装"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config(config_file)
        return cls._instance
    
    def __init__(self, config_file: str = None):
        """既に__new__で初期化済みなので何もしない"""
        pass
    
    def _load_config(self, config_file: Optional[str] = None) -> None:
        """設定ファイルを読み込む"""
        try:
            # デフォルトのパスを設定
            if config_file is None:
                # カレントディレクトリのconfig.jsonを検索
                if os.path.exists('config.json'):
                    config_file = 'config.json'
                # プロジェクトルートのconfig.jsonを検索
                elif os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')):
                    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
                else:
                    raise FileNotFoundError("設定ファイルが見つかりません")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                
            print(f"設定を読み込みました: {config_file}")
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")
            # 最低限の設定を用意
            self._config = {
                "obs": {
                    "host": "localhost",
                    "port": 4455,
                    "password": ""
                },
                "stream": {
                    "title": "自動配信テスト",
                    "description": "自動配信のテストです",
                    "privacy_status": "private",
                    "duration": 30,
                    "interval": 5,
                    "scenes": ["Scene"]
                }
            }
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """
        設定値を取得する
        
        Args:
            section: 設定セクション名（obs, stream, youtubeなど）
            key: キー名（省略時はセクション全体を返す）
            default: 設定が存在しない場合のデフォルト値
            
        Returns:
            設定値またはデフォルト値
        """
        if section not in self._config:
            return default
            
        if key is None:
            return self._config[section]
            
        return self._config[section].get(key, default)
    
    def get_obs_config(self) -> Dict[str, Any]:
        """OBS接続設定を取得する"""
        return self.get('obs', default={})
    
    def get_stream_config(self) -> Dict[str, Any]:
        """配信設定を取得する"""
        return self.get('stream', default={})
    
    def get_youtube_config(self) -> Dict[str, Any]:
        """YouTube設定を取得する"""
        return self.get('youtube', default={})
    
    def reload(self, config_file: str = None) -> None:
        """設定を再読み込みする"""
        self._load_config(config_file) 