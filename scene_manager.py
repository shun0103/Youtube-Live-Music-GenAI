"""
OBSのシーン管理機能を提供するモジュール
"""
import obsws_python as obsws
import datetime

class SceneManager:
    """OBSのシーンを管理するクラス"""
    
    def __init__(self, client):
        """
        SceneManagerを初期化する
        
        Args:
            client (obsws.ReqClient): OBS WebSocketリクエストクライアント
        """
        self.client = client
    
    def get_scenes(self):
        """
        利用可能なシーンのリストを取得する
        
        Returns:
            list: シーン名のリスト
        """
        scenes_response = self.client.get_scene_list()
        
        # レスポンスからシーン名を抽出
        if hasattr(scenes_response, 'scenes'):
            return [scene.get('sceneName', '') for scene in scenes_response.scenes]
        
        # バックアップ方法
        if isinstance(scenes_response, dict) and 'scenes' in scenes_response:
            return [scene.get('sceneName', '') for scene in scenes_response['scenes']]
            
        return []
    
    def switch_to_scene(self, scene_name):
        """
        指定したシーンに切り替える
        
        Args:
            scene_name (str): 切り替えるシーン名
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            available_scenes = self.get_scenes()
            print(f"利用可能なシーン: {available_scenes}")
            
            if scene_name in available_scenes:
                # OBS WebSocket v5
                self.client.set_current_program_scene(scene_name)
                print(f"シーンを {scene_name} に切り替えました")
                return True
            else:
                print(f"エラー: シーン '{scene_name}' は存在しません")
                return False
        except Exception as e:
            print(f"シーン切り替えエラー: {str(e)}")
            return False
    
    def get_current_scene(self):
        """
        現在のシーン名を取得する
        
        Returns:
            str: 現在のシーン名
        """
        response = self.client.get_current_program_scene()
        
        # レスポンスから直接シーン名を取得
        if hasattr(response, 'current_program_scene_name'):
            return response.current_program_scene_name
        
        # バックアップ方法
        if isinstance(response, dict):
            return response.get('currentProgramSceneName', '')
            
        return ""
    
    def update_text_source(self, source_name, text):
        """
        テキストソースの内容を更新する
        
        Args:
            source_name (str): テキストソースの名前
            text (str): 設定するテキスト内容
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            print(f"テキストソース '{source_name}' を更新: {text}")
            
            # OBS WebSocket v5のSetInputSettingsメソッドを使用
            self.client.send(
                "SetInputSettings",
                {
                    "inputName": source_name,
                    "inputSettings": {
                        "text": text
                    }
                }
            )
            return True
        except Exception as e:
            print(f"テキストソース更新エラー: {str(e)}")
            return False
    
    def update_date_text(self, source_name="text"):
        """
        指定されたテキストソースに現在の日付を[yyyy/MM/dd HH:mm:ss]形式で設定する
        
        Args:
            source_name (str): テキストソースの名前（デフォルト: "text"）
            
        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 現在の日付を[yyyy/MM/dd HH:mm:ss]形式で取得
            current_date = datetime.datetime.now().strftime("[%Y/%m/%d %H:%M:%S]")
            
            # テキストソースを更新
            return self.update_text_source(source_name, current_date)
        except Exception as e:
            print(f"日付テキスト更新エラー: {str(e)}")
            return False 