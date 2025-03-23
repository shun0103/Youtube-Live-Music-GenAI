"""
YouTubeクライアントのアダプター
"""
from typing import Dict, Any, Tuple, Optional
from src.domain.interfaces.youtube_interface import YouTubeLiveInterface
from src.infrastructure.youtube.youtube_client import YouTubeLiveController

class YouTubeLiveAdapter(YouTubeLiveInterface):
    """
    YouTubeLiveControllerをYouTubeLiveInterfaceに適合させるアダプタークラス
    """
    
    def __init__(self, client_secrets_file: str):
        """
        YouTubeLiveAdapterを初期化する
        
        Args:
            client_secrets_file (str): OAuthクライアントシークレットのJSONファイルパス
        """
        self.youtube_client = YouTubeLiveController(client_secrets_file)
    
    def create_broadcast(self, title: str, description: str, privacy_status: str, start_time=None) -> Dict[str, Any]:
        """
        ライブブロードキャストを作成する
        
        Args:
            title (str): ライブブロードキャストのタイトル
            description (str): 説明
            privacy_status (str): プライバシー設定 (public, private, unlisted)
            start_time: 配信開始予定時刻（オプション）
            
        Returns:
            Dict[str, Any]: ブロードキャスト情報の辞書
        """
        return self.youtube_client.create_broadcast(title, description, start_time, privacy_status)
    
    def create_stream(self) -> Tuple[str, str, str]:
        """
        ライブストリームを作成する
        
        Returns:
            Tuple[str, str, str]: (stream_id, rtmp_url, stream_key)
        """
        return self.youtube_client.create_stream()
    
    def bind_broadcast_to_stream(self, broadcast_id: str, stream_id: str) -> bool:
        """
        ブロードキャストとストリームをバインドする
        
        Args:
            broadcast_id (str): ブロードキャストID
            stream_id (str): ストリームID
            
        Returns:
            bool: 成功した場合はTrue
        """
        return self.youtube_client.bind_broadcast_to_stream(broadcast_id, stream_id)
    
    def start_broadcast(self, broadcast_id: str) -> bool:
        """
        ブロードキャストを開始する
        
        Args:
            broadcast_id (str): ブロードキャストID
            
        Returns:
            bool: 成功した場合はTrue
        """
        return self.youtube_client.start_broadcast(broadcast_id)
    
    def end_broadcast(self, broadcast_id: str) -> bool:
        """
        ブロードキャストを終了する
        
        Args:
            broadcast_id (str): ブロードキャストID
            
        Returns:
            bool: 成功した場合はTrue
        """
        return self.youtube_client.end_broadcast(broadcast_id)
    
    def get_broadcast_status(self, broadcast_id: str) -> str:
        """
        ブロードキャストのステータスを取得する
        
        Args:
            broadcast_id (str): ブロードキャストID
            
        Returns:
            str: ブロードキャストのステータス
        """
        return self.youtube_client.get_broadcast_status(broadcast_id)
    
    def setup_complete_live_stream(self, title: str, description: str, privacy_status: str) -> Tuple[str, str]:
        """
        完全なライブストリーム設定を行う
        
        Args:
            title (str): ライブブロードキャストのタイトル
            description (str): 説明
            privacy_status (str): プライバシー設定
            
        Returns:
            Tuple[str, str]: (broadcast_id, stream_key)
        """
        return self.youtube_client.setup_complete_live_stream(title, description, privacy_status) 