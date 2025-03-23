"""
配信設定を表すエンティティクラス
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class OBSConnectionSettings:
    """OBS接続設定"""
    host: str
    port: int
    password: str
    timeout: int = 30

@dataclass
class StreamSettings:
    """配信設定"""
    title: str
    description: str
    privacy_status: str
    scene_name: Optional[str] = None
    start_delay: int = 5
    duration: int = 30
    interval: int = 5
    scenes: List[str] = None
    
    def __post_init__(self):
        """初期化後の処理"""
        if self.scenes is None:
            self.scenes = ["Scene"]

@dataclass
class YouTubeSettings:
    """YouTube設定"""
    client_secrets: str

@dataclass
class StreamConfigModel:
    """配信設定全体のモデル"""
    obs: OBSConnectionSettings
    stream: StreamSettings
    youtube: Optional[YouTubeSettings] = None
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'StreamConfigModel':
        """辞書から設定モデルを作成する"""
        obs_dict = config_dict.get('obs', {})
        stream_dict = config_dict.get('stream', {})
        youtube_dict = config_dict.get('youtube', {})
        
        obs_settings = OBSConnectionSettings(
            host=obs_dict.get('host', 'localhost'),
            port=obs_dict.get('port', 4455),
            password=obs_dict.get('password', ''),
            timeout=obs_dict.get('timeout', 30)
        )
        
        stream_settings = StreamSettings(
            title=stream_dict.get('title', '自動配信テスト'),
            description=stream_dict.get('description', '自動配信のテストです'),
            privacy_status=stream_dict.get('privacy_status', 'private'),
            scene_name=stream_dict.get('scene_name'),
            start_delay=stream_dict.get('start_delay', 5),
            duration=stream_dict.get('duration', 30),
            interval=stream_dict.get('interval', 5),
            scenes=stream_dict.get('scenes', ["Scene"])
        )
        
        youtube_settings = None
        if youtube_dict and 'client_secrets' in youtube_dict:
            youtube_settings = YouTubeSettings(
                client_secrets=youtube_dict.get('client_secrets')
            )
        
        return cls(
            obs=obs_settings,
            stream=stream_settings,
            youtube=youtube_settings
        ) 