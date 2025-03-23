"""
YouTube Live APIを使って配信を制御するモジュール
"""
import os
import json
import datetime
import googleapiclient.discovery
import googleapiclient.errors
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import time

class YouTubeLiveController:
    """YouTubeのライブ配信を制御するクラス"""
    
    # YouTube Data API v3で必要なスコープ
    SCOPES = ["https://www.googleapis.com/auth/youtube"]
    
    def __init__(self, client_secrets_file, token_file="token.json"):
        """
        YouTubeLiveControllerを初期化する
        
        Args:
            client_secrets_file (str): OAuth 2.0クライアントシークレットのJSONファイルパス
            token_file (str): 認証トークンの保存先
        """
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.youtube = self._authenticate()
        self.current_broadcast_id = None
        self.current_stream_id = None
        
    def _authenticate(self):
        """
        YouTube APIの認証を行う
        
        Returns:
            googleapiclient.discovery.Resource: YouTube APIリソース
        """
        credentials = None
        
        # 保存済みのトークンがあればロード
        if os.path.exists(self.token_file):
            credentials = Credentials.from_authorized_user_info(
                json.load(open(self.token_file, 'r')), self.SCOPES)
        
        # トークンが無いか有効期限切れなら認証フローを実行
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, self.SCOPES)
                credentials = flow.run_local_server(port=0)
            
            # トークンを保存
            with open(self.token_file, 'w') as token:
                token.write(credentials.to_json())
        
        # YouTube API clientを構築
        return googleapiclient.discovery.build(
            "youtube", "v3", credentials=credentials)
    
    def create_broadcast(self, title, description="", start_time=None, privacy_status="public"):
        """
        配信の詳細情報(ブロードキャスト)を作成
        
        Args:
            title (str): 配信タイトル
            description (str): 配信の説明
            start_time (datetime or str): 配信開始予定時刻 (Noneの場合は現在時刻から1分後)
                                          文字列の場合はISO 8601形式("2023-01-01T00:00:00Z")
            privacy_status (str): プライバシー設定 ("public", "private", "unlisted")
            
        Returns:
            dict: 作成されたブロードキャスト情報
        """
        # デフォルトの開始時刻を現在から5分後に設定（余裕を持たせる）
        if start_time is None:
            start_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        
        # start_timeの型を確認し、適切に処理
        if isinstance(start_time, str):
            # 文字列の場合はそのまま使用（すでにISO形式と仮定）
            start_time_iso = start_time
        else:
            # datetime型の場合はISO形式に変換、UTCタイムゾーン付きで確実に
            if start_time.tzinfo is None:
                # タイムゾーン情報がない場合はUTCを設定
                start_time = start_time.replace(tzinfo=datetime.timezone.utc)
            start_time_iso = start_time.isoformat()
            
            # ISO形式の末尾に'Z'がない場合は追加（UTCを明示）
            if not start_time_iso.endswith('Z'):
                start_time_iso = start_time_iso.replace('+00:00', 'Z')
                if not start_time_iso.endswith('Z'):
                    start_time_iso += 'Z'
        
        print(f"設定する配信開始時刻: {start_time_iso}")
        
        # ブロードキャストの作成リクエスト
        try:
            request = self.youtube.liveBroadcasts().insert(
                part="snippet,status,contentDetails",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                        "scheduledStartTime": start_time_iso
                    },
                    "status": {
                        "privacyStatus": privacy_status
                    },
                    "contentDetails": {
                        "enableAutoStart": True,
                        "enableAutoStop": True
                    }
                }
            )
            
            response = request.execute()
            self.current_broadcast_id = response["id"]
            print(f"ブロードキャストを作成しました: ID = {self.current_broadcast_id}")
            return response
        except Exception as e:
            print(f"ブロードキャスト作成エラー: {e}")
            return None
    
    def create_stream(self, title="Primary Stream", description=""):
        """
        ストリーム(技術的な設定)を作成
        
        Args:
            title (str): ストリームタイトル
            description (str): ストリームの説明
            
        Returns:
            str: ストリームID
        """
        request = self.youtube.liveStreams().insert(
            part="snippet,cdn",
            body={
                "snippet": {
                    "title": title,
                    "description": description
                },
                "cdn": {
                    "frameRate": "variable",
                    "ingestionType": "rtmp",
                    "resolution": "variable"
                }
            }
        )
        
        response = request.execute()
        self.current_stream_id = response["id"]
        rtmp_url = response["cdn"]["ingestionInfo"]["ingestionAddress"]
        stream_key = response["cdn"]["ingestionInfo"]["streamName"]
        
        print(f"ストリームを作成しました: ID = {self.current_stream_id}")
        print(f"RTMP URL: {rtmp_url}")
        print(f"ストリームキー: {stream_key} (このキーをOBSに設定してください)")
        
        return self.current_stream_id, rtmp_url, stream_key
    
    def bind_broadcast_to_stream(self, broadcast_id=None, stream_id=None):
        """
        ブロードキャストとストリームを関連付ける
        
        Args:
            broadcast_id (str): ブロードキャストID (Noneの場合は最後に作成したもの)
            stream_id (str): ストリームID (Noneの場合は最後に作成したもの)
            
        Returns:
            bool: 成功した場合はTrue
        """
        broadcast_id = broadcast_id or self.current_broadcast_id
        stream_id = stream_id or self.current_stream_id
        
        if not broadcast_id or not stream_id:
            print("ブロードキャストまたはストリームIDが指定されていません")
            return False
        
        request = self.youtube.liveBroadcasts().bind(
            part="id,contentDetails",
            id=broadcast_id,
            streamId=stream_id
        )
        
        response = request.execute()
        print(f"ブロードキャストとストリームを関連付けました")
        return True
    
    def start_broadcast(self, broadcast_id=None):
        """
        ブロードキャストを開始する (ライブ配信開始)
        
        Args:
            broadcast_id (str): ブロードキャストID (Noneの場合は最後に作成したもの)
            
        Returns:
            bool: 成功した場合はTrue
        """
        broadcast_id = broadcast_id or self.current_broadcast_id
        
        if not broadcast_id:
            print("ブロードキャストIDが指定されていません")
            return False
        
        try:
            # 現在の状態を確認
            current_status = self.get_broadcast_status(broadcast_id)
            print(f"ブロードキャスト現在の状態: {current_status}")
            
            # 既にライブ状態の場合は成功とみなす
            if current_status == "live":
                print("ブロードキャストは既にライブ状態です")
                return True
                
            # 「ready」または「testing」状態の場合、少し待機して再度確認
            if current_status in ["ready", "testing"]:
                print("OBSからのストリームデータがYouTubeに到達するのを待機中...")
                for i in range(3):
                    time.sleep(3)  # 3秒待機
                    updated_status = self.get_broadcast_status(broadcast_id)
                    print(f"更新されたブロードキャスト状態: {updated_status}")
                    if updated_status == "live":
                        print("ブロードキャストは自動的にライブ状態になりました")
                        return True
            
            # 「ready」や「testing」状態からライブに移行できない場合、移行方法を変更
            if current_status in ["ready", "testing"]:
                print("YouTube APIを使用してブロードキャストをライブ状態に移行します...")
                
                # 代替方法：bindブロードキャストを再実行して強制的に進める
                try:
                    # このタイミングでブロードキャストとストリームを再関連付け
                    self.bind_broadcast_to_stream(broadcast_id, self.current_stream_id)
                    print("ブロードキャストとストリームを再関連付けしました")
                    
                    # 少し待機してから再度状態を確認
                    time.sleep(5)
                    updated_status = self.get_broadcast_status(broadcast_id)
                    print(f"再関連付け後のブロードキャスト状態: {updated_status}")
                    
                    if updated_status == "live":
                        print("ブロードキャストがライブ状態になりました")
                        return True
                except:
                    pass
            
            # それでも「live」状態にならない場合、標準の方法でトランジション
            try:
                request = self.youtube.liveBroadcasts().transition(
                    broadcastStatus="live",
                    id=broadcast_id,
                    part="id,status"
                )
                
                response = request.execute()
                status = response['status']['lifeCycleStatus']
                print(f"ブロードキャスト状態変更: {status}")
                return status == 'live'
            except googleapiclient.errors.HttpError as e:
                error_reason = str(e)
                
                # エラー理由を詳細に分析
                if 'redundantTransition' in error_reason:
                    print("冗長な状態遷移: ブロードキャストは既にライブ状態です")
                    return True
                elif 'invalidTransition' in error_reason:
                    # 特別なケース: OBSからのストリームがまだYouTubeに到達していない可能性
                    print(f"無効な状態遷移: 現在の状態 '{current_status}' からライブに移行できません")
                    print("OBSからのストリームデータが十分にYouTubeに送信されるのを待機しています...")
                    
                    # ユーザーに手動での確認を促す
                    print("YouTubeスタジオでブロードキャスト状態を確認して、")
                    print("ストリーム状態が「良好」になったら手動でライブ開始することをお勧めします。")
                    print("YouTube Studio URL: https://studio.youtube.com/channel/live")
                    
                    proceed = input("自動配信を続行せずにYouTubeスタジオでライブ開始しますか？ (y/n): ")
                    if proceed.lower() == 'y':
                        print("ライブ状態への移行をユーザーが手動で行うことを選択しました")
                        return True
                    
                    # 少し待機してから再度確認
                    print("もう少し待機して再度確認します...")
                    time.sleep(10)
                    final_status = self.get_broadcast_status(broadcast_id)
                    print(f"最終確認ブロードキャスト状態: {final_status}")
                    
                    if final_status == "live":
                        print("ブロードキャストがライブ状態になりました")
                        return True
                    
                    # それでも失敗する場合
                    return False
                else:
                    print(f"ライブ配信開始エラー: {str(e)}")
                    print("YouTubeエラーの詳細: " + error_reason[:200])
                    return False
        except Exception as e:
            print(f"ライブ配信開始エラー: {str(e)}")
            return False
    
    def end_broadcast(self, broadcast_id=None):
        """
        ブロードキャストを終了する (ライブ配信終了)
        
        Args:
            broadcast_id (str): ブロードキャストID (Noneの場合は最後に作成したもの)
            
        Returns:
            bool: 成功した場合はTrue
        """
        broadcast_id = broadcast_id or self.current_broadcast_id
        
        if not broadcast_id:
            print("ブロードキャストIDが指定されていません")
            return False
        
        request = self.youtube.liveBroadcasts().transition(
            broadcastStatus="complete",
            id=broadcast_id,
            part="id,status"
        )
        
        response = request.execute()
        print(f"ライブ配信を終了しました: {response['status']['lifeCycleStatus']}")
        return response['status']['lifeCycleStatus'] == 'complete'
    
    def list_broadcasts(self, max_results=5, broadcast_status="all"):
        """
        ライブ配信の一覧を取得
        
        Args:
            max_results (int): 取得する最大数
            broadcast_status (str): ステータスでフィルタ ("all", "active", "completed", "upcoming")
            
        Returns:
            list: ブロードキャスト情報のリスト
        """
        request = self.youtube.liveBroadcasts().list(
            part="id,snippet,contentDetails,status",
            broadcastStatus=broadcast_status,
            maxResults=max_results
        )
        
        response = request.execute()
        broadcasts = []
        
        for item in response.get("items", []):
            broadcast_info = {
                "id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "status": item["status"]["lifeCycleStatus"],
                "privacy": item["status"]["privacyStatus"],
                "scheduledStartTime": item["snippet"].get("scheduledStartTime")
            }
            broadcasts.append(broadcast_info)
        
        return broadcasts
    
    def get_broadcast_status(self, broadcast_id=None):
        """
        ブロードキャストの現在のステータスを取得
        
        Args:
            broadcast_id (str): ブロードキャストID (Noneの場合は最後に作成したもの)
            
        Returns:
            str: ステータス文字列 ('created', 'ready', 'testing', 'live', 'complete' など)
        """
        broadcast_id = broadcast_id or self.current_broadcast_id
        
        if not broadcast_id:
            print("ブロードキャストIDが指定されていません")
            return None
        
        request = self.youtube.liveBroadcasts().list(
            part="status",
            id=broadcast_id
        )
        
        response = request.execute()
        if not response.get("items"):
            return None
        
        return response["items"][0]["status"]["lifeCycleStatus"]
    
    def is_broadcast_live(self, broadcast_id=None):
        """
        ブロードキャストが現在ライブ中かどうかを確認
        
        Args:
            broadcast_id (str): ブロードキャストID (Noneの場合は最後に作成したもの)
            
        Returns:
            bool: ライブ中の場合はTrue
        """
        try:
            status = self.get_broadcast_status(broadcast_id)
            return status == "live"
        except Exception as e:
            print(f"ブロードキャスト状態チェックエラー: {str(e)}")
            return False
    
    def get_broadcast_url(self, broadcast_id=None):
        """
        ブロードキャストの視聴URL（YouTube配信URL）を取得
        
        Args:
            broadcast_id (str): ブロードキャストID (Noneの場合は最後に作成したもの)
            
        Returns:
            str: YouTube視聴URL
        """
        broadcast_id = broadcast_id or self.current_broadcast_id
        
        if not broadcast_id:
            print("ブロードキャストIDが指定されていません")
            return None
            
        return f"https://www.youtube.com/watch?v={broadcast_id}"
    
    def setup_complete_live_stream(self, title, description="", privacy_status="public"):
        """
        ライブストリームを一から設定する一連の処理
        
        Args:
            title (str): 配信タイトル
            description (str): 配信の説明
            privacy_status (str): プライバシー設定
            
        Returns:
            tuple: (ブロードキャストID, ストリームキー)
        """
        # 1. ブロードキャスト(動画メタデータ)作成
        broadcast_id = self.create_broadcast(title, description, privacy_status=privacy_status)
        
        # 2. ストリーム(技術設定)作成
        stream_id, rtmp_url, stream_key = self.create_stream(title + " - Stream")
        
        # 3. ブロードキャストとストリームの関連付け
        self.bind_broadcast_to_stream(broadcast_id, stream_id)
        
        # 配信URLを生成
        broadcast_url = self.get_broadcast_url(broadcast_id)
        
        print(f"ライブ配信の設定が完了しました")
        print(f"タイトル: {title}")
        print(f"配信URL: {broadcast_url}")
        print(f"OBSに以下の情報を設定してください:")
        print(f"URLとストリームキーをOBSの設定→配信→サービス「カスタム」に設定")
        print(f"サーバー: {rtmp_url}")
        print(f"ストリームキー: {stream_key}")
        
        return broadcast_id, stream_key
    
    def get_broadcast_info(self, broadcast_id=None):
        """
        ブロードキャストの詳細情報を取得
        
        Args:
            broadcast_id (str): ブロードキャストID (Noneの場合は最後に作成したもの)
            
        Returns:
            dict: ブロードキャスト情報、取得できない場合はNone
        """
        broadcast_id = broadcast_id or self.current_broadcast_id
        
        if not broadcast_id:
            print("ブロードキャストIDが指定されていません")
            return None
        
        try:
            request = self.youtube.liveBroadcasts().list(
                part="id,snippet,status,contentDetails",
                id=broadcast_id
            )
            
            response = request.execute()
            if not response.get("items"):
                return None
            
            item = response["items"][0]
            broadcast_info = {
                "id": item["id"],
                "snippet": item["snippet"],
                "status": item["status"],
                "contentDetails": item["contentDetails"]
            }
            
            return broadcast_info
        except Exception as e:
            print(f"ブロードキャスト情報の取得エラー: {str(e)}")
            return None 