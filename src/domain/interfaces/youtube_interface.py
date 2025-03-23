"""
YouTubeライブ配信のインターフェース
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional

class YouTubeLiveInterface(ABC):
    """YouTubeライブ配信の操作インターフェース"""
    
    @abstractmethod
    def create_broadcast(self, title: str, description: str, privacy_status: str) -> Dict[str, Any]:
        """ライブブロードキャストを作成する"""
        pass
    
    @abstractmethod
    def create_stream(self) -> Tuple[str, str, str]:
        """ライブストリームを作成する
        
        Returns:
            Tuple[str, str, str]: (stream_id, rtmp_url, stream_key)
        """
        pass
    
    @abstractmethod
    def bind_broadcast_to_stream(self, broadcast_id: str, stream_id: str) -> bool:
        """ブロードキャストとストリームをバインドする"""
        pass
    
    @abstractmethod
    def start_broadcast(self, broadcast_id: str) -> bool:
        """ブロードキャストを開始する"""
        pass
    
    @abstractmethod
    def end_broadcast(self, broadcast_id: str) -> bool:
        """ブロードキャストを終了する"""
        pass
    
    @abstractmethod
    def get_broadcast_status(self, broadcast_id: str) -> str:
        """ブロードキャストのステータスを取得する"""
        pass
    
    @abstractmethod
    def setup_complete_live_stream(self, title: str, description: str, privacy_status: str) -> Tuple[str, str]:
        """完全なライブストリーム設定を行う
        
        Returns:
            Tuple[str, str]: (broadcast_id, stream_key)
        """
        pass 