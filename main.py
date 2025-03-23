"""
OBSとYouTubeを連携した自動配信プログラム
"""
import os
import time
import sys
import argparse
import obsws_python as obsws
import json
from integrated_controller import IntegratedLiveController
from obs_connection import OBSConnection
from scene_manager import SceneManager
from stream_control import StreamController

def load_config(config_file):
    """設定ファイルを読み込む"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"設定ファイルの読み込みエラー: {e}")
        return None

def main():
    """メイン処理"""
    try:
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(description='OBSとYouTubeを統合した自動配信システム')
        parser.add_argument('--config', default='config.json', help='設定ファイルのパス (デフォルト: config.json)')
        parser.add_argument('--skip-youtube', action='store_true', help='YouTubeライブ配信をスキップしてOBSのみを使用')
        args = parser.parse_args()
        
        # 設定ファイルを読み込む
        config = load_config(args.config)
        if not config:
            sys.exit(1)
        
        # OBS接続設定（timeoutパラメータを除外）
        obs_config = {k: v for k, v in config.get('obs', {}).items() if k != 'timeout'}
        
        # YouTubeのクライアントシークレットファイル
        client_secrets = None if args.skip_youtube else config.get('youtube', {}).get('client_secrets')
        
        if not args.skip_youtube and not client_secrets:
            print("警告: YouTubeのクライアントシークレットファイルが設定されていません")
            proceed = input("YouTubeライブ配信をスキップしてOBSのみで続行しますか？ (y/n): ")
            if proceed.lower() != 'y':
                print("処理を中止します")
                sys.exit(1)
            args.skip_youtube = True
        
        # OBSが起動しているか確認
        print("OBS接続テスト中...")
        try:
            # タイムアウトパラメータを直接指定 
            test_client = obsws.ReqClient(
                host=obs_config["host"],
                port=obs_config["port"],
                password=obs_config["password"]
            )
            # バージョン情報取得でテスト
            version = test_client.get_version()
            print(f"OBS Studio バージョン: {version.obs_version}")
            print(f"OBS WebSocket バージョン: {version.obs_web_socket_version}")
            test_client.disconnect()
        except Exception as e:
            print(f"OBS接続エラー: {str(e)}")
            print("OBS Studioが起動しているか、WebSocketの設定が正しいか確認してください。")
            print(f"接続設定: ホスト={obs_config['host']}, ポート={obs_config['port']}")
            retry = input("OBSへの接続を再試行しますか？ (y/n): ")
            if retry.lower() != 'y':
                return
        
        # 統合コントローラーを初期化
        if args.skip_youtube:
            # OBSのみのコントローラー初期化（YouTube APIをスキップ）
            obs_connection = OBSConnection(**obs_config)
            client = obs_connection.connect()
            print("OBS WebSocketに接続しました")
            print("OBS WebSocketイベントリスナーを開始しました")
            
            scene_manager = SceneManager(client)
            stream_controller = StreamController(client, scene_manager, config_file=args.config)
            
            controller = IntegratedLiveController(None, obs_config, client=client, scene_manager=scene_manager, stream_controller=stream_controller)
        else:
            # 通常の統合コントローラー初期化
            controller = IntegratedLiveController(client_secrets, obs_config, config_file=args.config)
        
        # 配信設定
        title = config.get('stream', {}).get('title', '自動配信テスト')
        description = config.get('stream', {}).get('description', '自動配信のテストです')
        privacy_status = config.get('stream', {}).get('privacy_status', 'public')
        scene_name = config.get('stream', {}).get('scene_name')
        start_delay = config.get('stream', {}).get('start_delay', 5)
        
        # 配信開始
        result = controller.start_integrated_stream(
            title=title,
            description=description,
            privacy_status=privacy_status,
            scene_name=scene_name,
            start_delay=start_delay
        )
        
        if not result:
            print("配信開始に失敗しました")
            sys.exit(1)
        
        print("配信を開始しました。終了するにはCtrl+Cを押してください。")
        
        # ユーザーが止めるまで実行
        try:
            input("終了するにはEnterキーを押してください...")
        except KeyboardInterrupt:
            print("ユーザーによって配信が中断されました")
        
        # 配信終了
        controller.stop_integrated_stream()
        print("配信が終了しました")
        
    except KeyboardInterrupt:
        print("ユーザーによって処理が中断されました")
        try:
            controller.stop_integrated_stream()
        except:
            pass
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        try:
            controller.stop_integrated_stream()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()