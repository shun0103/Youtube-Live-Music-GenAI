"""
クリーンアーキテクチャに基づいたOBSとYouTubeを連携した自動配信プログラム
"""
import os
import time
import sys
import argparse

from src.config.settings import ConfigManager
from src.domain.entities.stream_settings import StreamConfigModel
from src.infrastructure.obs.obs_client import OBSClient
from src.infrastructure.obs.scene_manager import SceneManager
from src.infrastructure.obs.stream_controller import OBSStreamController
from src.infrastructure.youtube.youtube_adapter import YouTubeLiveAdapter
from src.application.services.stream_service import StreamService

def main():
    """メイン処理"""
    try:
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(description='OBSとYouTubeを統合した自動配信システム')
        parser.add_argument('--config', default='config.json', help='設定ファイルのパス (デフォルト: config.json)')
        parser.add_argument('--skip-youtube', action='store_true', help='YouTubeライブ配信をスキップしてOBSのみを使用')
        args = parser.parse_args()
        
        # 設定を読み込む
        config_manager = ConfigManager(args.config)
        
        # 設定からモデルを作成
        config_dict = {
            'obs': config_manager.get_obs_config(),
            'stream': config_manager.get_stream_config(),
            'youtube': config_manager.get_youtube_config() if not args.skip_youtube else None
        }
        config_model = StreamConfigModel.from_dict(config_dict)
        
        # YouTubeのクライアントシークレットファイル
        client_secrets = None if args.skip_youtube else config_model.youtube.client_secrets if config_model.youtube else None
        
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
            # OBS接続の作成
            obs_client = OBSClient(
                host=config_model.obs.host,
                port=config_model.obs.port,
                password=config_model.obs.password
            )
            # テスト接続
            test_client = obs_client.connect()
            
            # バージョン情報取得でテスト
            version = test_client.get_version()
            print(f"OBS Studio バージョン: {version.obs_version}")
            print(f"OBS WebSocket バージョン: {version.obs_web_socket_version}")
            
            # テスト接続はいったん切断
            obs_client.disconnect()
        except Exception as e:
            print(f"OBS接続エラー: {str(e)}")
            print("OBS Studioが起動しているか、WebSocketの設定が正しいか確認してください。")
            print(f"接続設定: ホスト={config_model.obs.host}, ポート={config_model.obs.port}")
            retry = input("OBSへの接続を再試行しますか？ (y/n): ")
            if retry.lower() != 'y':
                return
        
        # 各コンポーネントの初期化
        # インフラストラクチャレイヤー
        obs_client = OBSClient(
            host=config_model.obs.host,
            port=config_model.obs.port,
            password=config_model.obs.password
        )
        client = obs_client.connect()
        scene_manager = SceneManager(client)
        stream_controller = OBSStreamController(client, scene_manager, config_file=args.config)
        
        # YouTubeコントローラーの初期化（必要な場合）
        youtube_controller = None
        if not args.skip_youtube and client_secrets:
            youtube_controller = YouTubeLiveAdapter(client_secrets)
        
        # アプリケーションサービスの初期化
        stream_service = StreamService(
            obs_connection=obs_client,
            scene_manager=scene_manager,
            stream_controller=stream_controller,
            youtube_controller=youtube_controller
        )
        
        # 配信設定
        title = config_model.stream.title
        description = config_model.stream.description
        privacy_status = config_model.stream.privacy_status
        scene_name = config_model.stream.scene_name
        start_delay = config_model.stream.start_delay
        
        # 配信開始
        result = stream_service.start_integrated_stream(
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
        stream_service.stop_integrated_stream()
        print("配信が終了しました")
        
    except KeyboardInterrupt:
        print("ユーザーによって処理が中断されました")
        try:
            stream_service.stop_integrated_stream()
        except:
            pass
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        try:
            stream_service.stop_integrated_stream()
        except:
            pass
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 