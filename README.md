# OBS自動配信コントローラー

## 概要
このプロジェクトは、OBSのWebSocket APIを使用して、YouTube配信を自動的に開始し、指定された時間間隔でシーンを切り替えるツールです。

## 前提条件
- OBS Studio（バージョン28以上推奨）
- OBS WebSocketプラグイン（OBS Studio 28以上では標準搭載）
- Python 3.7以上

## インストール方法
1. プロジェクトをクローンまたはダウンロードする
2. 依存関係をインストールする
```bash
pip install -r requirements.txt
```

## 設定方法
1. `config.py`を編集して、OBSのWebSocket設定を更新する
   - `OBS_HOST`: OBSが実行されているマシンのホスト名またはIPアドレス（通常は`localhost`）
   - `OBS_PORT`: OBSのWebSocketポート（デフォルトは4455）
   - `OBS_PASSWORD`: OBS WebSocketのパスワード
   - `DEFAULT_SCENES`: OBSに実際に存在するシーン名を設定
   - `DEFAULT_STREAM_DURATION`: 配信の合計時間（秒）
   - `DEFAULT_SCENE_INTERVAL`: シーン切り替えの間隔（秒）

2. OBS内で設定
   - YouTubeのストリームキーを設定
   - WebSocketサーバーが有効になっていることを確認
   - 使用するシーンが作成されていることを確認

## 使用方法
1. OBSを起動する
2. スクリプトを実行する
```bash
python main.py
```

3. プログラムは以下を行います：
   - OBS WebSocketサーバーに接続
   - 配信を開始
   - 設定された間隔で指定されたシーンを切り替え
   - 設定された時間が経過したら配信を停止

## プロジェクト構成
- `main.py`: メインプログラム
- `config.py`: アプリケーション設定
- `obs_connection.py`: OBS WebSocket接続管理
- `scene_manager.py`: シーン管理
- `stream_control.py`: 配信制御
- `requirements.txt`: 依存関係リスト
- `README.md`: このファイル

## トラブルシューティング
- "指定されたシーンが見つかりません" - OBSに実際に存在するシーン名を`config.py`に設定してください
- "接続エラー" - OBSが実行されていること、WebSocketサーバーが有効になっていることを確認してください
- "認証エラー" - パスワードが正しいことを確認してください 