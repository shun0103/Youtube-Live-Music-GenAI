"""
統合配信サービスのモジュール
"""
import time
import threading
from typing import Optional, List, Dict, Any, Tuple

from src.domain.entities.stream_settings import StreamConfigModel
from src.domain.interfaces.obs_interface import OBSConnectionInterface, SceneManagerInterface, StreamControlInterface
from src.domain.interfaces.youtube_interface import YouTubeLiveInterface

class StreamService:
    """統合配信サービスクラス"""
    
    def __init__(
        self,
        obs_connection: OBSConnectionInterface,
        scene_manager: SceneManagerInterface,
        stream_controller: StreamControlInterface,
        youtube_controller: Optional[YouTubeLiveInterface] = None
    ):
        """
        配信サービスを初期化する
        
        Args:
            obs_connection: OBS接続インターフェース
            scene_manager: シーン管理インターフェース
            stream_controller: 配信制御インターフェース
            youtube_controller: YouTubeライブ配信コントローラー（オプショナル）
        """
        self.obs_connection = obs_connection
        self.scene_manager = scene_manager
        self.stream_controller = stream_controller
        self.youtube_controller = youtube_controller
        
        # 状態管理
        self.broadcast_id = None
        self.stream_key = None
        self.is_obs_configured = False
        
        # 日付テキスト更新用のタイマー
        self.date_update_timer = None
        self.date_update_running = False
        self.date_update_interval = 10  # 10秒ごとに更新
    
    def setup_youtube_live(self, title: str, description: str = "", privacy_status: str = "public") -> bool:
        """
        YouTubeライブ配信の設定を行う
        
        Args:
            title: 配信タイトル
            description: 配信の説明
            privacy_status: プライバシー設定
            
        Returns:
            bool: 成功した場合はTrue
        """
        if not self.youtube_controller:
            print("YouTubeコントローラーが設定されていません")
            return False
            
        try:
            # YouTubeライブの設定を作成
            self.broadcast_id, self.stream_key = self.youtube_controller.setup_complete_live_stream(
                title, description, privacy_status)
            return True
        except Exception as e:
            print(f"YouTube配信設定エラー: {str(e)}")
            return False
    
    def configure_obs_for_youtube(self, rtmp_url: str, stream_key: str) -> bool:
        """
        OBSをYouTube配信用に設定する
        
        Args:
            rtmp_url: RTMP URL
            stream_key: ストリームキー
            
        Returns:
            bool: 成功した場合はTrue
        """
        try:
            # OBS WebSocket v5 API を使用して配信設定を行う
            client = self.obs_connection.get_client()
            
            # 配信状態を確認
            is_streaming = self.stream_controller.is_streaming()
            if is_streaming:
                print("警告: OBSは既に配信中です。配信中は設定を変更できません。")
                self.is_obs_configured = True
                return True
            
            # 配信設定の作成
            settings = {
                "server": rtmp_url,
                "key": stream_key
            }
            
            # 詳細なレスポンスの確認
            print("OBSのストリーミング設定を更新中...")
            response = client.send(
                "SetStreamServiceSettings",
                {
                    "streamServiceType": "rtmp_custom",
                    "streamServiceSettings": settings
                }
            )
            
            print(f"設定更新レスポンス: {response}")
            self.is_obs_configured = True
            return True
                
        except Exception as e:
            print(f"OBS設定エラー: {str(e)}")
            print("\n以下の設定を手動で行ってください:")
            print("1. OBSの「設定」→「配信」を開く")
            print("2. サービスを「カスタム」に設定")
            print(f"3. サーバーに「{rtmp_url}」を入力")
            print(f"4. ストリームキーに「{stream_key}」を入力")
            
            input("\nOBSの設定が完了したらEnterキーを押してください...")
            return False
    
    def start_integrated_stream(
        self,
        title: str = "自動配信テスト",
        description: str = "自動配信のテストです",
        privacy_status: str = "public",
        scene_name: Optional[str] = None,
        start_delay: int = 5
    ) -> bool:
        """
        統合配信を開始する
        
        Args:
            title: 配信タイトル
            description: 配信の説明
            privacy_status: プライバシー設定（public/private/unlisted）
            scene_name: 切り替える場面名。Noneの場合は切り替えなし
            start_delay: OBSストリーミング開始から配信開始までの遅延（秒）
            
        Returns:
            bool: 成功したらTrue
        """
        try:
            # YouTubeの準備（コントローラーがある場合のみ）
            rtmp_url = None
            stream_key = None
            
            if self.youtube_controller:
                print("YouTubeライブ配信を準備中...")
                # ブロードキャスト作成
                broadcast = self.youtube_controller.create_broadcast(
                    title=title, 
                    description=description, 
                    privacy_status=privacy_status,
                    start_time=None  # 明示的にNoneを渡す (コントローラーが現在時刻+5分を自動設定)
                )
                if not broadcast:
                    print("ブロードキャスト作成に失敗しました")
                    return False
                
                self.broadcast_id = broadcast['id']
                print(f"ブロードキャストを作成しました: {self.broadcast_id}")
                
                # ストリーム作成
                stream_id, rtmp_url, stream_key = self.youtube_controller.create_stream()
                if not stream_id:
                    print("ストリーム作成に失敗しました")
                    return False
                
                # ブロードキャストとストリームをバインド
                if not self.youtube_controller.bind_broadcast_to_stream(self.broadcast_id, stream_id):
                    print("ブロードキャストとストリームのバインドに失敗しました")
                    return False
                
                # RTMPとストリームキーを取得
                self.stream_key = stream_key
                
                print(f"RTMP URL: {rtmp_url}")
                print(f"ストリームキー: {self.stream_key[:5]}...")  # セキュリティのため全部は表示しない
                
                # OBSにYouTube設定をセットアップ
                if not self.configure_obs_for_youtube(rtmp_url, self.stream_key):
                    print("OBSのYouTube設定に失敗しました")
                    return False
                
                self.is_obs_configured = True
            else:
                print("YouTubeライブ配信をスキップします")
            
            # OBSのシーン切り替え（指定があれば）
            if scene_name:
                if not self.scene_manager.switch_to_scene(scene_name):
                    print(f"シーン '{scene_name}' への切り替えに失敗しました")
                    return False
            
            # 日付テキスト更新タイマーを開始
            self._start_date_text_updater()
                
            # OBSのストリーミング開始
            if not self.stream_controller.start_streaming():
                print("OBSのストリーミング開始に失敗しました")
                return False
                
            # YouTubeのブロードキャスト開始（コントローラーがある場合のみ）
            if self.youtube_controller and self.broadcast_id:
                # 少し遅延を入れてOBSのストリーミングが始まるのを待つ
                print(f"OBSストリーミングを開始しました。{start_delay}秒後にYouTube配信を開始します...")
                time.sleep(start_delay)
                
                # ストリーミングの実際の開始を待機
                if not self.stream_controller.wait_for_stream_start(timeout=60):
                    print("警告: ストリーミングの開始を確認できませんでした。続行します。")
                
                # ブロードキャストをライブ状態に遷移
                if not self.youtube_controller.start_broadcast(self.broadcast_id):
                    print("ブロードキャストのライブ開始に失敗しました")
                    return False
                    
                print(f"配信が開始されました！ YouTube URL: https://www.youtube.com/watch?v={self.broadcast_id}")
            else:
                print("OBSのストリーミングを開始しました。")
            
            return True
            
        except Exception as e:
            print(f"統合配信の開始中にエラーが発生しました: {e}")
            # トレースバックを出力
            import traceback
            traceback.print_exc()
            return False
    
    def stop_integrated_stream(self) -> bool:
        """
        統合配信を停止する
        
        Returns:
            bool: 成功したらTrue
        """
        success = True
        
        try:
            # 日付テキスト更新タイマーを停止
            self._stop_date_text_updater()
            
            # OBSのストリーミングを停止
            print("OBSのストリーミングを停止中...")
            if not self.stream_controller.stop_streaming():
                print("OBSのストリーミング停止に失敗しました")
                success = False
            
            # YouTubeのブロードキャストを終了（コントローラーがある場合のみ）
            if self.youtube_controller and self.broadcast_id:
                print("YouTubeブロードキャストを終了中...")
                if not self.youtube_controller.end_broadcast(self.broadcast_id):
                    print("YouTubeブロードキャストの終了に失敗しました")
                    success = False
                else:
                    print("YouTubeブロードキャストを正常に終了しました")
            
            # 接続をクリーンアップ
            self.obs_connection.disconnect()
            
            return success
            
        except Exception as e:
            print(f"統合配信の停止中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _start_date_text_updater(self):
        """日付テキストの更新を開始する"""
        if self.date_update_timer is None:
            self.date_update_timer = threading.Timer(self.date_update_interval, self._update_date_text)
            self.date_update_timer.daemon = True
            self.date_update_timer.start()
            self.date_update_running = True

    def _update_date_text(self):
        """日付テキストを更新する"""
        try:
            # [yyyy/MM/dd HH:mm:ss]形式で日付を取得
            current_date = time.strftime("[%Y/%m/%d %H:%M:%S]")
            print(f"日付テキストを更新: {current_date}")
            
            # OBSのテキストソースを更新
            self.scene_manager.update_text_source("text", current_date)
            
            # 次の更新のためにタイマーを再スタート（プログラムが実行中の場合）
            if self.date_update_running:
                self.date_update_timer = threading.Timer(self.date_update_interval, self._update_date_text)
                self.date_update_timer.daemon = True
                self.date_update_timer.start()
        except Exception as e:
            print(f"日付テキスト更新エラー: {e}")
            # エラーがあっても次の更新を試みる
            if self.date_update_running:
                self.date_update_timer = threading.Timer(self.date_update_interval, self._update_date_text)
                self.date_update_timer.daemon = True
                self.date_update_timer.start()

    def _stop_date_text_updater(self):
        """日付テキストの更新を停止する"""
        if self.date_update_timer:
            self.date_update_timer.cancel()
            self.date_update_timer = None
            self.date_update_running = False 