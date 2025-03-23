"""
OBS WebSocket接続を管理するモジュール
"""
import obsws_python as obsws

class OBSConnection:
    """OBS WebSocketサーバーへの接続を管理するクラス"""
    
    def __init__(self, host="localhost", port=4455, password=""):
        """
        OBS WebSocketへの接続を初期化する
        
        Args:
            host (str): ホスト名またはIPアドレス
            port (int): ポート番号（OBS WebSocket v5のデフォルトは4455）
            password (str): WebSocketサーバーのパスワード
        """
        self.host = host
        self.port = port
        self.password = password
        self.client = None
    
    def connect(self):
        """OBS WebSocketサーバーに接続する"""
        self.client = obsws.ReqClient(
            host=self.host, 
            port=self.port, 
            password=self.password
        )
        # obsws-pythonライブラリでは、クライアントが正常に作成されたら接続されています
        print("OBS WebSocketに接続しました")
        return self.client
    
    def disconnect(self):
        """OBS WebSocketサーバーから切断する"""
        if self.client:
            # obsws-pythonでは明示的なdisconnectは必要ありません
            self.client = None
            print("OBS WebSocketから切断しました")
    
    def get_client(self):
        """
        WebSocketクライアントを取得する
        
        Returns:
            obsws.ReqClient: 接続済みのクライアントインスタンス
        """
        if not self.client:
            self.connect()
        return self.client 