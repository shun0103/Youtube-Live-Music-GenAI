"""
OBSの配信制御機能を提供するモジュール
"""
import time
import threading
import obsws_python as obsws
import json

class StreamController:
    """OBSの配信を制御するクラス"""
    
    def __init__(self, client, scene_manager, config_file="config.json"):
        """
        StreamControllerを初期化する
        
        Args:
            client (obsws.ReqClient): OBS WebSocketリクエストクライアント
            scene_manager (SceneManager): シーン管理インスタンス
            config_file (str): 設定ファイルのパス
        """
        self.client = client
        self.scene_manager = scene_manager
        self.streaming = False
        self.streaming_event = threading.Event()
        
        # OBS接続情報をconfig.jsonから取得
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                conn_params = config.get('obs', {})
        except Exception as e:
            print(f"設定ファイルの読み込みエラー: {e}")
            # デフォルト値を設定
            conn_params = {
                "host": "localhost",
                "port": 4455,
                "password": ""
            }
        
        # イベントクライアントを作成
        self.event_client = obsws.EventClient(
            host=conn_params["host"],
            port=conn_params["port"],
            password=conn_params["password"]
        )
        
        # イベントハンドラを登録
        self.event_client.callback.register(self._on_stream_status)
        print("OBS WebSocketイベントリスナーを開始しました")
    
    def _on_stream_status(self, message):
        """
        配信状態変更イベントのコールバック
        
        Args:
            message: OBS WebSocketからのメッセージ
        """
        try:
            # イベント情報をデバッグ出力
            print(f"配信イベント受信: {message}")
            
            # イベントタイプがストリーム開始イベントかどうかを確認
            event_type = getattr(message, 'eventType', None)
            if event_type is None:
                try:
                    event_type = message.getEventType()
                except:
                    event_type = str(message)
            
            print(f"イベントタイプ: {event_type}")
            
            # ストリーム開始イベントの処理（v4とv5で異なる）
            if 'StreamStarted' in str(event_type) or 'OutputStateChanged' in str(event_type) or 'OutputActive' in str(event_type):
                try:
                    # イベントデータを取得（v5形式）
                    event_data = None
                    try:
                        event_data = message.getEventData()
                    except:
                        # v5でない場合は他の方法を試す
                        event_data = message
                    
                    print(f"イベントデータ: {event_data}")
                    
                    # 出力状態をチェック
                    output_active = False
                    
                    # v5: outputActiveフィールドをチェック
                    if hasattr(event_data, 'outputActive'):
                        output_active = event_data.outputActive
                    elif isinstance(event_data, dict) and 'outputActive' in event_data:
                        output_active = event_data['outputActive']
                    # v4: outputStateフィールドをチェック
                    elif hasattr(event_data, 'outputState'):
                        output_active = event_data.outputState == 'OBS_WEBSOCKET_OUTPUT_STARTED'
                    elif isinstance(event_data, dict) and 'outputState' in event_data:
                        output_active = event_data['outputState'] == 'OBS_WEBSOCKET_OUTPUT_STARTED'
                    
                    if output_active:
                        print("ストリーム開始イベントを検出！")
                        self.streaming_event.set()
                    
                except Exception as e:
                    print(f"イベントデータ処理エラー: {e}")
        except Exception as e:
            print(f"ストリームイベント処理エラー: {e}")
    
    def start_streaming(self):
        """
        配信を開始する
        
        Returns:
            bool: 成功した場合はTrue
        """
        try:
            # 既に配信中かどうかを確認
            is_streaming = self.is_streaming()
            if is_streaming:
                print("既にOBS配信中です - 新たに開始コマンドは送信しません")
                self.streaming_event.set()  # イベントをセット
                return True
                
            # obs-websocket v5のStartStreamコマンドを送信
            print("配信開始リクエストを送信しました")
            response = self.client.send("StartStream")
            print(f"配信開始レスポンス: {response}")
            
            # 配信ステータスを取得して確認
            time.sleep(2)  # 少し待ってからステータスを確認
            status = self.is_streaming()
            print(f"配信開始直後のステータス: {status}")
            
            if status:
                self.streaming_event.set()  # イベントをセット
            
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"配信開始エラー: {error_msg}")
            
            # エラーメッセージが「既に配信中」を示す場合
            if "already active" in error_msg.lower():
                print("OBSは既に配信中です")
                self.streaming_event.set()  # イベントをセット
                return True
                
            return False
    
    def stop_streaming(self):
        """
        配信を停止する
        
        Returns:
            bool: 成功した場合はTrue
        """
        try:
            # 現在配信中かどうかを確認
            is_streaming = self.is_streaming()
            if not is_streaming:
                print("OBSは既に配信停止しています")
                self.streaming_event.clear()  # イベントをクリア
                return True
                
            # 配信停止リクエストを送信
            print("配信停止リクエストを送信しました")
            self.client.send("StopStream")
            print("配信を停止しました")
            
            # イベント状態をクリア
            self.streaming_event.clear()
            
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"配信停止エラー: {error_msg}")
            
            # エラーメッセージが「既に停止している」を示す場合
            if "not active" in error_msg.lower():
                print("OBSは既に配信停止しています")
                self.streaming_event.clear()
                return True
                
            return False
    
    def is_streaming(self):
        """
        現在配信中かどうかを確認する
        
        Returns:
            bool: 配信中の場合はTrue
        """
        try:
            # obsws-pythonではGetStreamStatusの戻り値はクラスインスタンス
            response = self.client.send("GetStreamStatus")
            print(f"GetStreamStatus レスポンス: {response}")
            
            # デバッグ情報を詳細に表示
            if hasattr(response, '__dict__'):
                print(f"レスポンスの__dict__: {response.__dict__}")
            
            # obsws-pythonでは属性名はoutput_activeを使用
            if hasattr(response, 'output_active'):
                streaming = response.output_active
                print(f"output_active属性の値: {streaming}")
                return streaming
            elif isinstance(response, dict) and 'outputActive' in response:
                streaming = response['outputActive']
                print(f"outputActive属性の値: {streaming}")
                return streaming
            
            # レスポンスの属性を表示
            attrs = dir(response)
            print(f"レスポンスの全属性: {attrs}")
            
            # 文字列表現に'output_active: True'が含まれているか確認
            response_str = str(response)
            print(f"レスポンスの文字列表現: {response_str}")
            if "output_active: True" in response_str.lower():
                return True
            
            # とにかく直接配信を試行する（最終手段）
            return False
        except Exception as e:
            print(f"配信状態確認エラー: {str(e)}")
            return False
    
    def wait_for_stream_start(self, timeout=60):
        """
        配信が実際に開始されるまで待機する
        
        Args:
            timeout (int): 最大待機時間（秒）
            
        Returns:
            bool: 配信が開始された場合はTrue、タイムアウトした場合はFalse
        """
        print(f"配信開始を待機中...（最大{timeout}秒）")
        
        # すでに配信中なら即時True
        if self.is_streaming():
            print("すでに配信中です")
            return True
            
        # イベント待機
        started = self.streaming_event.wait(timeout)
        if started:
            print("配信開始を確認しました")
            return True
        
        # イベントでの確認に失敗した場合、直接ステータスを取得して再確認
        print("イベントでの配信開始確認タイムアウト - 直接ステータスを確認します")
        try:
            # 直接OBSにストリーミング状態を問い合わせ
            is_active = self.is_streaming()
            if is_active:
                print("直接確認: 配信は開始されています")
                return True
            else:
                print("直接確認: 配信は開始されていません")
                return False
        except Exception as e:
            print(f"配信状態確認エラー: {e}")
            return False
    
    def auto_stream_with_scene_switch(self, duration, scenes, interval):
        """
        指定した時間、指定したシーンを順番に切り替えながら配信する
        
        Args:
            duration (int): 配信する合計時間（秒）
            scenes (list): 切り替えるシーン名のリスト
            interval (int): シーンを切り替える間隔（秒）
        """
        # 配信開始
        self.start_streaming()
        
        # 配信が実際に開始されるまで待機
        if not self.wait_for_stream_start(timeout=60):
            print("配信開始タイムアウト: 60秒以内に配信が開始されませんでした")
            self.stop_streaming()
            return
        
        print(f"配信が開始されました。{duration}秒間の配信を行います")
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                for scene in scenes:
                    if time.time() - start_time >= duration:
                        break
                    self.scene_manager.switch_to_scene(scene)
                    time.sleep(interval)
        except KeyboardInterrupt:
            print("ユーザーによって配信が中断されました")
        finally:
            self.stop_streaming()
            
    def __del__(self):
        """デストラクタ：イベントクライアントを解放"""
        try:
            if hasattr(self, 'event_client') and self.event_client:
                # obsws-pythonのEventClientにはstopメソッドがないので、リファレンスを解放
                print("OBS WebSocketイベントリスナーをクリア")
                self.event_client = None
        except Exception as e:
            print(f"イベントリスナー解放エラー: {str(e)}")
    
    def check_streaming_output(self):
        """
        現在のOBSストリーミング出力状態を確認する
        
        Returns:
            dict: OBSストリーミング統計情報
        """
        try:
            # ストリーム統計情報を取得
            response = self.client.send("GetStreamStatus")
            
            if hasattr(response, '__dict__'):
                stats = response.__dict__
                
                # 必要な情報を抽出して表示
                output_active = getattr(response, 'output_active', False)
                kbits_per_sec = getattr(response, 'kbits_per_sec', 0)
                congestion = getattr(response, 'congestion', 0)
                fps = getattr(response, 'fps', 0)
                reconnecting = getattr(response, 'reconnecting', False)
                
                print(f"\n==== OBSストリーム出力統計 ====")
                print(f"配信状態: {'有効' if output_active else '無効'}")
                print(f"ビットレート: {kbits_per_sec} kbps")
                print(f"混雑度: {congestion:.2f}")
                print(f"FPS: {fps}")
                print(f"再接続中: {'はい' if reconnecting else 'いいえ'}")
                
                # ビットレートが低すぎる場合は警告
                if output_active and kbits_per_sec < 500:
                    print(f"警告: ビットレートが低すぎます！({kbits_per_sec} kbps)")
                    print("OBSの出力設定 > ストリーミングでビットレートを確認してください。")
                    
                # 混雑度が高すぎる場合は警告
                if output_active and congestion > 0.8:
                    print(f"警告: ネットワーク混雑度が高すぎます！({congestion:.2f})")
                    print("インターネット接続またはOBSのビットレート設定を確認してください。")
                    
                # FPSが低すぎる場合は警告
                if output_active and fps < 15:
                    print(f"警告: FPSが低すぎます！({fps})")
                    print("コンピュータの負荷またはOBSのFPS設定を確認してください。")
                
                return {
                    "output_active": output_active,
                    "kbits_per_sec": kbits_per_sec,
                    "congestion": congestion,
                    "fps": fps,
                    "reconnecting": reconnecting
                }
            
            return {"output_active": False}
        except Exception as e:
            print(f"ストリーム統計取得エラー: {str(e)}")
            return {"output_active": False, "error": str(e)}
    
    def monitor_stream_health(self, duration=30, interval=5):
        """
        指定した期間、ストリーム状態を監視する
        
        Args:
            duration (int): 監視時間（秒）
            interval (int): チェック間隔（秒）
            
        Returns:
            bool: 問題がなければTrue、問題があればFalse
        """
        if not self.is_streaming():
            print("ストリームが開始されていないため、監視を開始できません")
            return False
        
        print(f"\n配信状態を{duration}秒間監視します（{interval}秒間隔）...")
        start_time = time.time()
        all_ok = True
        
        try:
            while time.time() - start_time < duration:
                remaining = int(duration - (time.time() - start_time))
                print(f"\n残り{remaining}秒の監視...")
                
                # ストリーム統計情報を取得
                stats = self.check_streaming_output()
                
                # 出力がアクティブでないか、ビットレートが0の場合は問題があるとみなす
                if (not stats.get("output_active", False) or 
                    stats.get("kbits_per_sec", 0) < 100):
                    print(f"警告: ストリーム出力に問題が検出されました！")
                    print("OBSが映像データを正しく送信していない可能性があります。")
                    all_ok = False
                
                # 混雑度が非常に高い場合
                if stats.get("congestion", 0) > 0.9:
                    print(f"警告: ネットワーク混雑度が非常に高いです！")
                    print("インターネット接続が不安定かもしれません。")
                    all_ok = False
                
                time.sleep(interval)
            
            if all_ok:
                print("\nストリーム監視完了: 問題は検出されませんでした")
            else:
                print("\nストリーム監視完了: 問題が検出されました")
                print("OBSの設定とビデオソースを確認してください")
            
            return all_ok
        except KeyboardInterrupt:
            print("\nユーザーによって監視が中断されました")
            return False
        except Exception as e:
            print(f"\nストリーム監視エラー: {str(e)}")
            return False 