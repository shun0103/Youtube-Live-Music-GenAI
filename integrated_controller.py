"""
YouTubeとOBSを連携させた統合配信コントローラー
"""
from obs_connection import OBSConnection
from scene_manager import SceneManager
from stream_control import StreamController
from youtube_live_api import YouTubeLiveController
import obsws_python as obsws
import time
import threading
import os
import json

class IntegratedLiveController:
    """YouTubeとOBSを連携させた統合配信コントローラークラス"""
    
    def __init__(self, youtube_client_secrets, obs_config, client=None, scene_manager=None, stream_controller=None, config_file="config.json"):
        """
        統合配信コントローラーを初期化する
        
        Args:
            youtube_client_secrets (str): OAuth 2.0クライアントシークレットのJSONファイルパス、Noneの場合はYouTube機能を無効化
            obs_config (dict): OBS接続設定
            client (obsws.ReqClient, optional): 既存のOBS WebSocketクライアント
            scene_manager (SceneManager, optional): 既存のSceneManagerインスタンス
            stream_controller (StreamController, optional): 既存のStreamControllerインスタンス
            config_file (str): 設定ファイルのパス
        """
        # YouTubeコントローラー初期化（クライアントシークレットがある場合のみ）
        self.youtube_controller = None
        if youtube_client_secrets:
            self.youtube_controller = YouTubeLiveController(youtube_client_secrets)
        
        # OBS接続（既存のクライアントがあればそれを使用）
        if client and scene_manager and stream_controller:
            self.client = client
            self.scene_manager = scene_manager
            self.stream_controller = stream_controller
            self.obs_connection = None  # 既存の接続を使用するため不要
        else:
            # timeoutパラメータを除外（OBSConnectionはtimeoutを受け付けない）
            obs_connection_config = {k: v for k, v in obs_config.items() if k != 'timeout'}
            
            # 新しく接続を作成
            self.obs_connection = OBSConnection(**obs_connection_config)
            self.client = self.obs_connection.connect()
            
            # OBSコントローラー初期化
            self.scene_manager = SceneManager(self.client)
            self.stream_controller = StreamController(self.client, self.scene_manager, config_file=config_file)
        
        # 状態管理
        self.broadcast_id = None
        self.stream_key = None
        self.is_obs_configured = False
        
        # 日付テキスト更新用のタイマー
        self.date_update_timer = None
        self.date_update_running = False
        self.date_update_interval = 10  # 10秒ごとに更新
    
    def setup_youtube_live(self, title, description="", privacy_status="public"):
        """
        YouTubeライブ配信の設定を行う
        
        Args:
            title (str): 配信タイトル
            description (str): 配信の説明
            privacy_status (str): プライバシー設定
            
        Returns:
            bool: 成功した場合はTrue
        """
        try:
            # YouTubeライブの設定を作成
            self.broadcast_id, self.stream_key = self.youtube_controller.setup_complete_live_stream(
                title, description, privacy_status)
            return True
        except Exception as e:
            print(f"YouTube配信設定エラー: {str(e)}")
            return False
    
    def configure_obs_for_youtube(self, rtmp_url, stream_key):
        """
        OBSをYouTube配信用に設定する
        
        Args:
            rtmp_url (str): RTMP URL
            stream_key (str): ストリームキー
            
        Returns:
            bool: 成功した場合はTrue
        """
        try:
            # 現在の配信状態を確認
            print("現在のOBS配信状態を確認中...")
            is_streaming = False
            try:
                is_streaming = self.stream_controller.is_streaming()
                print(f"現在の配信状態: {'配信中' if is_streaming else '配信していない'}")
            except Exception as e:
                print(f"配信状態確認エラー: {str(e)}")
            
            # 既に配信中なら設定変更をスキップ
            if is_streaming:
                print("警告: OBSは既に配信中です。配信中は設定を変更できません。")
                print("現在の配信を継続します。")
                
                # それでも設定を確認
                try:
                    current_settings = self.client.send("GetStreamServiceSettings")
                    if hasattr(current_settings, 'streamServiceSettings'):
                        settings = current_settings.streamServiceSettings
                        current_server = settings.get('server', '') if isinstance(settings, dict) else getattr(settings, 'server', '')
                        current_key = settings.get('key', '') if isinstance(settings, dict) else getattr(settings, 'key', '')
                        
                        if current_server == rtmp_url and current_key == stream_key:
                            print("現在の配信設定は正しいYouTube設定です。")
                            self.is_obs_configured = True
                            return True
                        else:
                            print("警告: 現在の配信設定がYouTubeの設定と異なります。")
                            print(f"期待: サーバー={rtmp_url}, キー={stream_key[:5]}...")
                            print(f"現在: サーバー={current_server}, キー={current_key[:5] if current_key else 'なし'}...")
                            
                            print("\n配信中のため設定を変更できません。手動で設定するか、配信を停止してから再試行してください。")
                            print("\n次の設定を手動で入力してください:")
                            print(f"サーバー: {rtmp_url}")
                            print(f"ストリームキー: {stream_key}")
                            
                            input("\nOBSの設定が完了したらEnterキーを押してください...")
                            return False
                except Exception as e:
                    print(f"現在の設定確認エラー: {str(e)}")
                    
                self.is_obs_configured = True
                return True
            
            # 設定前の状態を確認
            print("現在のOBS配信設定を確認中...")
            current_settings = None
            try:
                current_settings = self.client.send("GetStreamServiceSettings")
                if hasattr(current_settings, 'streamServiceType'):
                    print(f"現在の配信サービスタイプ: {current_settings.streamServiceType}")
                if hasattr(current_settings, 'streamServiceSettings'):
                    settings = current_settings.streamServiceSettings
                    current_server = settings.get('server', '') if isinstance(settings, dict) else getattr(settings, 'server', '')
                    current_key = settings.get('key', '') if isinstance(settings, dict) else getattr(settings, 'key', '')
                    print(f"現在のサーバー: {current_server}")
                    print(f"現在のキー: {current_key[:5]}..." if current_key else "現在のキー: なし")
            except Exception as e:
                print(f"現在の設定確認エラー: {str(e)}")
            
            # OBS WebSocket v5 API を使用して配信設定を行う
            setting_success = False
            try:
                # 配信設定の作成
                settings = {
                    "server": rtmp_url,
                    "key": stream_key
                }
                
                # 詳細なレスポンスの確認
                print("OBSのストリーミング設定を更新中...")
                response = self.client.send(
                    "SetStreamServiceSettings",
                    {
                        "streamServiceType": "rtmp_custom",
                        "streamServiceSettings": settings
                    }
                )
                
                print(f"設定更新レスポンス: {response}")
                print(f"レスポンスタイプ: {type(response)}")
                
                if hasattr(response, 'status') and response.status == 'error':
                    print(f"設定エラー: {getattr(response, 'error', 'unknown error')}")
                    setting_success = False
                else:
                    print("OBSのストリーミング設定を更新しました")
                    setting_success = True
                
            except Exception as e:
                print(f"OBS WebSocket設定エラー: {str(e)}")
                setting_success = False
            
            # 設定が成功したか確認
            if setting_success:
                # 設定が反映されているか確認
                try:
                    print("設定が正しく反映されているか確認中...")
                    time.sleep(1)  # 設定が反映されるのを少し待つ
                    
                    verify_settings = self.client.send("GetStreamServiceSettings")
                    if hasattr(verify_settings, 'streamServiceType'):
                        service_type = verify_settings.streamServiceType
                        if service_type != "rtmp_custom":
                            print(f"警告: 配信サービスタイプが期待と異なります: {service_type}")
                            setting_success = False
                    
                    if hasattr(verify_settings, 'streamServiceSettings'):
                        settings = verify_settings.streamServiceSettings
                        verify_server = settings.get('server', '') if isinstance(settings, dict) else getattr(settings, 'server', '')
                        verify_key = settings.get('key', '') if isinstance(settings, dict) else getattr(settings, 'key', '')
                        
                        if verify_server != rtmp_url:
                            print(f"警告: サーバー設定が反映されていません")
                            print(f"期待: {rtmp_url}")
                            print(f"実際: {verify_server}")
                            setting_success = False
                        
                        if verify_key != stream_key:
                            print(f"警告: ストリームキー設定が反映されていません")
                            print(f"期待: {stream_key[:5]}...")
                            print(f"実際: {verify_key[:5]}..." if verify_key else "なし")
                            setting_success = False
                        
                        if verify_server == rtmp_url and verify_key == stream_key:
                            print("設定が正しく反映されました")
                            self.is_obs_configured = True
                except Exception as e:
                    print(f"設定確認エラー: {str(e)}")
                    setting_success = False
            
            # 設定に失敗した場合、ユーザーに手動設定を促す
            if not setting_success:
                print("\n自動設定に失敗しました。以下の設定を手動で行ってください:")
                print("1. OBSの「設定」→「配信」を開く")
                print("2. サービスを「カスタム」に設定")
                print(f"3. サーバーに「{rtmp_url}」を入力")
                print(f"4. ストリームキーに「{stream_key}」を入力")
                print("5. 「OK」をクリックして設定を保存")
                
                input("\nOBSの設定が完了したらEnterキーを押してください...")
                
                # 設定を再確認
                try:
                    verify_settings = self.client.send("GetStreamServiceSettings")
                    if hasattr(verify_settings, 'streamServiceSettings'):
                        settings = verify_settings.streamServiceSettings
                        verify_server = settings.get('server', '') if isinstance(settings, dict) else getattr(settings, 'server', '')
                        verify_key = settings.get('key', '') if isinstance(settings, dict) else getattr(settings, 'key', '')
                        
                        if verify_server == rtmp_url and verify_key == stream_key:
                            print("手動設定が正しく行われました")
                            self.is_obs_configured = True
                            return True
                        else:
                            print("警告: 手動設定後も設定が正しくありません")
                            print(f"期待: サーバー={rtmp_url}, キー={stream_key[:5]}...")
                            print(f"実際: サーバー={verify_server}, キー={verify_key[:5] if verify_key else 'なし'}...")
                            print("配信は続行されますが、YouTube側に正しく配信されない可能性があります")
                            return False
                except Exception as e:
                    print(f"手動設定確認エラー: {str(e)}")
                    print("設定確認に失敗しましたが、処理を続行します")
                    return False
            
            return setting_success
                
        except Exception as e:
            print(f"OBS設定エラー: {str(e)}")
            print("\n以下の設定を手動で行ってください:")
            print("1. OBSの「設定」→「配信」を開く")
            print("2. サービスを「カスタム」に設定")
            print(f"3. サーバーに「{rtmp_url}」を入力")
            print(f"4. ストリームキーに「{stream_key}」を入力")
            
            input("\nOBSの設定が完了したらEnterキーを押してください...")
            return False
    
    def start_integrated_stream(self, title="自動配信テスト", description="自動配信のテストです", privacy_status="public", scene_name=None, start_delay=5):
        """
        統合配信を開始する
        
        Args:
            title (str): 配信タイトル
            description (str): 配信の説明
            privacy_status (str): プライバシー設定（public/private/unlisted）
            scene_name (str, optional): 切り替える場面名。Noneの場合は切り替えなし
            start_delay (int): OBSストリーミング開始から配信開始までの遅延（秒）
            
        Returns:
            bool: 成功したらTrue
        """
        try:
            # YouTubeの準備（コントローラーがある場合のみ）
            if self.youtube_controller:
                print("YouTubeライブ配信を準備中...")
                # ブロードキャスト作成（パラメータ名を明示的に指定）
                broadcast = self.youtube_controller.create_broadcast(
                    title=title, 
                    description=description, 
                    privacy_status=privacy_status
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
                
                # RTMPとストリームキーを取得（既に上のcreate_streamで取得済み）
                self.stream_key = stream_key
                
                print(f"RTMP URL: {rtmp_url}")
                print(f"ストリームキー: {self.stream_key[:5]}...")  # セキュリティのため全部は表示しない
                
                # OBSにYouTube設定をセットアップ
                if not self.configure_obs_for_youtube(rtmp_url, self.stream_key):
                    print("OBSのYouTube設定に失敗しました")
                    return False
                
                self.is_obs_configured = True
            else:
                print("YouTubeライブ配信をスキップします（--skip-youtubeオプションが指定されました）")
            
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
    
    def _auto_scene_switching(self, scenes, interval, duration):
        """
        指定した時間、指定したシーンを自動的に切り替える
        
        Args:
            scenes (list): シーン名のリスト
            interval (int): シーン切り替え間隔（秒）
            duration (int): 配信時間（秒）
        """
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                for scene in scenes:
                    if time.time() - start_time >= duration:
                        break
                    self.scene_manager.switch_to_scene(scene)
                    time.sleep(interval)
            
            # 時間経過後に配信を終了
            self.stop_integrated_stream()
        except Exception as e:
            print(f"シーン切り替えエラー: {str(e)}")
            self.stop_integrated_stream()
    
    def _continuous_scene_switching(self, scenes, interval):
        """
        無限に指定したシーンを切り替え続ける（別スレッドで実行）
        
        Args:
            scenes (list): シーン名のリスト
            interval (int): シーン切り替え間隔（秒）
        """
        try:
            while True:
                for scene in scenes:
                    self.scene_manager.switch_to_scene(scene)
                    time.sleep(interval)
        except Exception as e:
            print(f"シーン切り替えエラー: {str(e)}")
    
    def stop_integrated_stream(self):
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
            if self.obs_connection:
                self.obs_connection.disconnect()
            
            return success
            
        except Exception as e:
            print(f"統合配信の停止中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _verify_scene_has_sources(self, scene_name):
        """
        指定されたシーンにビデオソースが含まれているか確認する
        
        Args:
            scene_name (str): 確認するシーン名
            
        Returns:
            bool: ビデオソースが含まれている場合はTrue
        """
        try:
            # シーンのアイテム一覧を取得
            print(f"\n=== '{scene_name}' のソース確認 ===")
            response = self.client.send("GetSceneItemList", {"sceneName": scene_name})
            
            # デバッグ情報の出力
            print(f"GetSceneItemList レスポンス型: {type(response)}")
            print(f"レスポンスのdir: {dir(response)}")
            
            if hasattr(response, '__dict__'):
                print(f"レスポンスの__dict__: {response.__dict__}")
            
            # 直接データアクセスを試みる
            try:
                data = response.d if hasattr(response, 'd') else None
                print(f"response.d: {data}")
            except Exception as e:
                print(f"データアクセスエラー: {e}")
            
            # 生データの取得を試みる
            try:
                print(f"response.responseData: {getattr(response, 'responseData', None)}")
            except Exception as e:
                print(f"responseDataアクセスエラー: {e}")
                
            # レスポンスのJSONダンプを試みる    
            try:
                import json
                if hasattr(response, 'responseData'):
                    print(f"レスポンスJSON: {json.dumps(response.responseData)}")
            except Exception as e:
                print(f"JSONダンプエラー: {e}")
            
            # sceneItemsプロパティがない場合の処理
            scene_items = None
            if hasattr(response, 'sceneItems'):
                scene_items = response.sceneItems
            elif hasattr(response, 'responseData') and isinstance(response.responseData, dict):
                scene_items = response.responseData.get('sceneItems')
            
            if not scene_items:
                print(f"警告: シーン '{scene_name}' にはアイテムが含まれていません")
                return False
                
            # アイテムの一覧を表示
            print(f"\nシーン '{scene_name}' に含まれるアイテム:")
            has_video_source = False
            
            for item in scene_items:
                # デバッグ情報
                print(f"アイテム型: {type(item)}")
                if hasattr(item, '__dict__'):
                    print(f"アイテム__dict__: {item.__dict__}")
                elif isinstance(item, dict):
                    print(f"アイテムdict: {item}")
                else:
                    print(f"アイテムdir: {dir(item)}")
                
                # アイテム情報の取得試行
                item_name = None
                item_type = None
                item_enabled = True
                
                # 属性またはディクショナリからのアクセス
                if hasattr(item, 'sourceName'):
                    item_name = item.sourceName
                elif isinstance(item, dict) and 'sourceName' in item:
                    item_name = item['sourceName']
                else:
                    try:
                        item_name = getattr(item, 'sourceName', 'Unknown')
                    except:
                        try:
                            item_name = item.get('sourceName', 'Unknown')
                        except:
                            item_name = 'Unknown'
                
                # 入力タイプの取得
                if hasattr(item, 'inputKind'):
                    item_type = item.inputKind
                elif isinstance(item, dict) and 'inputKind' in item:
                    item_type = item['inputKind']
                elif hasattr(item, 'sourceKind'):
                    item_type = item.sourceKind
                elif isinstance(item, dict) and 'sourceKind' in item:
                    item_type = item['sourceKind']
                else:
                    try:
                        item_type = getattr(item, 'inputKind', 'Unknown')
                    except:
                        try:
                            item_type = item.get('inputKind', 'Unknown')
                        except:
                            item_type = 'Unknown'
                
                # 有効状態の取得
                if hasattr(item, 'sceneItemEnabled'):
                    item_enabled = item.sceneItemEnabled
                elif isinstance(item, dict) and 'sceneItemEnabled' in item:
                    item_enabled = item['sceneItemEnabled']
                else:
                    try:
                        item_enabled = getattr(item, 'sceneItemEnabled', True)
                    except:
                        try:
                            item_enabled = item.get('sceneItemEnabled', True)
                        except:
                            item_enabled = True
                
                status = "有効" if item_enabled else "無効"
                print(f" - [{status}] {item_name} (タイプ: {item_type})")
                
                # ビデオソースのタイプをチェック
                video_source_types = ['dshow_input', 'av_capture_input', 'video_capture_device', 
                                     'ffmpeg_source', 'browser_source', 'vlc_source', 'monitor_capture',
                                     'window_capture', 'game_capture', 'image_source', 'color_source',
                                     'media_source', 'ndi_source']
                                     
                if item_type in video_source_types and item_enabled:
                    has_video_source = True
            
            if not has_video_source:
                print(f"\n警告: シーン '{scene_name}' に有効なビデオソースが見つかりません！")
                print("シーンには少なくとも1つの有効なビデオソース（カメラ、画像、ウィンドウキャプチャなど）が必要です。")
                return False
                
            return True
        except Exception as e:
            print(f"シーンソース確認エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return True  # エラーの場合は安全のためTrueを返す
            
    def verify_obs_streaming_setup(self):
        """
        OBSの配信設定が正しく行われているか検証する
        
        Returns:
            bool: 設定が正しい場合はTrue
        """
        try:
            # ストリーミング設定の確認
            print("\n==== OBS配信設定の確認 ====")
            
            # 1. ストリーミングサービスの設定を確認
            try:
                service_settings = self.client.send("GetStreamServiceSettings")
                if hasattr(service_settings, 'streamServiceType'):
                    print(f"配信サービスタイプ: {service_settings.streamServiceType}")
                    
                    # rtmp_customかどうか確認
                    if service_settings.streamServiceType != "rtmp_custom":
                        print(f"警告: 配信サービスが「カスタム」に設定されていません")
                        return False
                        
                    # 設定の確認
                    if hasattr(service_settings, 'streamServiceSettings'):
                        settings = service_settings.streamServiceSettings
                        server = settings.get('server', '') if isinstance(settings, dict) else getattr(settings, 'server', '')
                        stream_key = settings.get('key', '') if isinstance(settings, dict) else getattr(settings, 'key', '')
                        
                        if not server or not server.startswith("rtmp://a.rtmp.youtube.com"):
                            print(f"警告: サーバーURLがYouTube用に正しく設定されていません")
                            print(f"現在の設定: {server}")
                            print(f"期待される設定: rtmp://a.rtmp.youtube.com/live2")
                            return False
                            
                        if not stream_key:
                            print(f"警告: ストリームキーが設定されていません")
                            return False
                            
                        print(f"YouTubeストリーミング設定は正しく行われています")
            except Exception as e:
                print(f"ストリーミングサービス設定の確認エラー: {str(e)}")
                return False
                
            # 2. 出力設定の確認
            try:
                output_settings = self.client.send("GetVideoSettings")
                if hasattr(output_settings, 'outputWidth') and hasattr(output_settings, 'outputHeight'):
                    width = output_settings.outputWidth
                    height = output_settings.outputHeight
                    print(f"出力解像度: {width}x{height}")
                    
                    if width < 640 or height < 360:
                        print(f"警告: 出力解像度が低すぎます（最低推奨: 640x360）")
            except Exception as e:
                print(f"出力設定の確認エラー: {str(e)}")
                
            # 3. ストリーミング状態の確認
            try:
                is_streaming = self.stream_controller.is_streaming()
                print(f"現在のストリーミング状態: {'配信中' if is_streaming else '配信していない'}")
            except Exception as e:
                print(f"ストリーミング状態の確認エラー: {str(e)}")
                
            # 4. シーンの確認
            available_scenes = self.scene_manager.get_scenes()
            if not available_scenes:
                print(f"警告: OBSにシーンがありません")
                return False
                
            # 少なくとも1つのシーンにビデオソースがあるか確認
            has_valid_scene = False
            for scene in available_scenes:
                if self._verify_scene_has_sources(scene):
                    has_valid_scene = True
                    break
                    
            if not has_valid_scene:
                print(f"\n警告: 有効なビデオソースを含むシーンが見つかりませんでした")
                print("OBSでシーンを編集し、カメラやウィンドウキャプチャなどのビデオソースを追加してください。")
                return False
                
            return True
            
        except Exception as e:
            print(f"OBS設定検証エラー: {str(e)}")
            return False 

    def _start_date_text_updater(self):
        """
        日付テキストの更新を開始する
        """
        if self.date_update_timer is None:
            self.date_update_timer = threading.Timer(self.date_update_interval, self._update_date_text)
            self.date_update_timer.start()
            self.date_update_running = True

    def _update_date_text(self):
        """
        日付テキストを更新する
        """
        try:
            # [yyyy/MM/dd HH:mm:ss]形式で日付を取得
            current_date = time.strftime("[%Y/%m/%d %H:%M:%S]")
            print(f"日付テキストを更新: {current_date}")
            
            # OBSのテキストソースを更新
            self.scene_manager.update_text_source("text", current_date)
            
            # 次の更新のためにタイマーを再スタート（プログラムが実行中の場合）
            if self.date_update_running:
                self.date_update_timer = threading.Timer(self.date_update_interval, self._update_date_text)
                self.date_update_timer.daemon = True  # メインスレッド終了時に自動終了
                self.date_update_timer.start()
        except Exception as e:
            print(f"日付テキスト更新エラー: {e}")
            # エラーがあっても次の更新を試みる
            self._start_date_text_updater()

    def _stop_date_text_updater(self):
        """
        日付テキストの更新を停止する
        """
        if self.date_update_timer:
            self.date_update_timer.cancel()
            self.date_update_timer = None
            self.date_update_running = False 