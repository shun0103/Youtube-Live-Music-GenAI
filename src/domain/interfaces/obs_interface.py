"""
OBSの操作に関するインターフェース
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

class OBSConnectionInterface(ABC):
    """OBS接続のインターフェース"""
    
    @abstractmethod
    def connect(self) -> Any:
        """OBSに接続する"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """OBSから切断する"""
        pass
    
    @abstractmethod
    def get_client(self) -> Any:
        """WebSocketクライアントを取得する"""
        pass

class SceneManagerInterface(ABC):
    """シーン管理のインターフェース"""
    
    @abstractmethod
    def get_scenes(self) -> List[str]:
        """OBSで利用可能なシーンのリストを取得する"""
        pass
    
    @abstractmethod
    def switch_to_scene(self, scene_name: str) -> bool:
        """指定したシーンに切り替える"""
        pass
    
    @abstractmethod
    def update_text_source(self, source_name: str, text: str) -> bool:
        """指定したテキストソースのテキストを更新する"""
        pass

class StreamControlInterface(ABC):
    """配信制御のインターフェース"""
    
    @abstractmethod
    def start_streaming(self) -> bool:
        """配信を開始する"""
        pass
    
    @abstractmethod
    def stop_streaming(self) -> bool:
        """配信を停止する"""
        pass
    
    @abstractmethod
    def is_streaming(self) -> bool:
        """現在配信中かどうかを確認する"""
        pass
    
    @abstractmethod
    def wait_for_stream_start(self, timeout: int = 60) -> bool:
        """配信が実際に開始されるまで待機する"""
        pass 