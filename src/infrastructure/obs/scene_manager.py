"""
OBSのシーン管理機能を提供するモジュール
"""
import obsws_python as obsws
from typing import List, Optional, Dict, Any
from src.domain.interfaces.obs_interface import SceneManagerInterface

class SceneManager(SceneManagerInterface):
    """OBSのシーンを管理するクラス"""
    
    def __init__(self, client: obsws.ReqClient):
        """
        SceneManagerを初期化する
        
        Args:
            client (obsws.ReqClient): OBS WebSocketリクエストクライアント
        """
        self.client = client
    
    def get_scenes(self) -> List[str]:
        """
        OBSで利用可能なシーンのリストを取得する
        
        Returns:
            list: シーン名のリスト
        """
        try:
            # OBS WebSocket v5 APIを使用
            response = self.client.send("GetSceneList")
            
            # レスポンスの処理方法はAPIのバージョンによって異なる
            scenes = []
            
            if hasattr(response, 'scenes'):
                # 直接scenesアトリビュートが存在する場合
                scenes_data = response.scenes
                if isinstance(scenes_data, list):
                    for scene in scenes_data:
                        if isinstance(scene, dict) and 'sceneName' in scene:
                            scenes.append(scene['sceneName'])
                        elif hasattr(scene, 'sceneName'):
                            scenes.append(scene.sceneName)
            
            # 別の形式の場合（辞書形式など）
            elif hasattr(response, '__dict__') and 'scenes' in response.__dict__:
                scenes_data = response.__dict__['scenes']
                if isinstance(scenes_data, list):
                    for scene in scenes_data:
                        if isinstance(scene, dict) and 'sceneName' in scene:
                            scenes.append(scene['sceneName'])
                        elif hasattr(scene, 'sceneName'):
                            scenes.append(scene.sceneName)
            
            # プロパティ属性から取得を試みる
            elif hasattr(response, 'getScenes'):
                scenes_data = response.getScenes()
                if isinstance(scenes_data, list):
                    for scene in scenes_data:
                        if isinstance(scene, dict) and 'sceneName' in scene:
                            scenes.append(scene['sceneName'])
                        elif hasattr(scene, 'sceneName'):
                            scenes.append(scene.sceneName)
            
            # responseDataプロパティから取得を試みる
            elif hasattr(response, 'responseData'):
                response_data = response.responseData
                if isinstance(response_data, dict) and 'scenes' in response_data:
                    scenes_data = response_data['scenes']
                    if isinstance(scenes_data, list):
                        for scene in scenes_data:
                            if isinstance(scene, dict) and 'sceneName' in scene:
                                scenes.append(scene['sceneName'])
                            elif hasattr(scene, 'sceneName'):
                                scenes.append(scene.sceneName)
            
            # 最終手段：クラスの全属性をダンプして調査
            if not scenes:
                print("シーンリストを取得できません - レスポンス形式が不明です")
                print(f"レスポンスのタイプ: {type(response)}")
                print(f"レスポンスの属性: {dir(response)}")
                if hasattr(response, '__dict__'):
                    print(f"レスポンスの__dict__: {response.__dict__}")
            
            print(f"利用可能なシーン: {scenes}")
            return scenes
        except Exception as e:
            print(f"シーンリスト取得エラー: {str(e)}")
            return []
    
    def switch_to_scene(self, scene_name: str) -> bool:
        """
        指定したシーンに切り替える
        
        Args:
            scene_name (str): 切り替え先のシーン名
            
        Returns:
            bool: 成功した場合はTrue
        """
        try:
            # 利用可能なシーンを確認
            available_scenes = self.get_scenes()
            
            # 指定されたシーンが存在するか確認
            if scene_name not in available_scenes:
                print(f"シーン '{scene_name}' は存在しません")
                print(f"利用可能なシーン: {available_scenes}")
                return False
            
            # obs-websocket v5のSetCurrentProgramSceneコマンドを使用
            self.client.send("SetCurrentProgramScene", {"sceneName": scene_name})
            print(f"シーンを '{scene_name}' に切り替えました")
            return True
        except Exception as e:
            print(f"シーン切り替えエラー: {str(e)}")
            return False
    
    def update_text_source(self, source_name: str, text: str) -> bool:
        """
        テキストソースのテキストを更新する
        
        Args:
            source_name (str): テキストソースの名前
            text (str): 新しいテキスト内容
            
        Returns:
            bool: 成功した場合はTrue
        """
        try:
            # 現在のシーンに依存せずに直接入力設定を更新
            # OBS WebSocket v5の SetInputSettings リクエストを使用
            print(f"テキストソース '{source_name}' を更新: {text}")
            
            # シンプルな実装 - 直接SetInputSettingsコマンドを使用
            try:
                response = self.client.send(
                    "SetInputSettings",
                    {
                        "inputName": source_name,
                        "inputSettings": {
                            "text": text
                        }
                    }
                )
                print(f"テキスト更新レスポンス: {response}")
                return True
            except Exception as e:
                print(f"テキスト更新エラー (1): {str(e)}")
                
                # 入力を確認してみる
                try:
                    inputs = self.client.send("GetInputList")
                    print(f"利用可能な入力一覧: {inputs}")
                    
                    # 入力が存在するか確認
                    input_exists = False
                    if hasattr(inputs, 'inputs'):
                        for input_item in inputs.inputs:
                            input_name = None
                            if isinstance(input_item, dict) and 'inputName' in input_item:
                                input_name = input_item['inputName']
                            elif hasattr(input_item, 'inputName'):
                                input_name = input_item.inputName
                                
                            if input_name == source_name:
                                input_exists = True
                                break
                    
                    if not input_exists:
                        print(f"警告: 入力ソース '{source_name}' が見つかりません")
                        print("テキストソースを作成する必要があります")
                        return False
                    
                    # 最終的に再度試行
                    response = self.client.send(
                        "SetInputSettings",
                        {
                            "inputName": source_name,
                            "inputSettings": {
                                "text": text
                            }
                        }
                    )
                    return True
                except Exception as list_error:
                    print(f"入力リスト取得エラー: {str(list_error)}")
                    return False
        except Exception as e:
            print(f"テキストソース更新エラー (2): {str(e)}")
            return False
    
    def _get_current_scene(self) -> Optional[str]:
        """
        現在のシーン名を取得する
        
        Returns:
            str or None: 現在のシーン名、または取得できない場合はNone
        """
        try:
            # obs-websocket v5では、GetCurrentProgramSceneでシーン名を取得
            response = self.client.send("GetCurrentProgramScene")
            
            # OBS WebSocket v5固有のレスポンス処理を追加
            try:
                # データクラスのattrsメソッドを使ってアクセス
                if hasattr(response, '__class__') and hasattr(response, '__dict__'):
                    if 'current_program_scene_name' in response.__dict__:
                        return response.__dict__['current_program_scene_name']
                    elif 'scene_name' in response.__dict__:
                        return response.__dict__['scene_name']
                
                # データクラスの直接アクセス
                if hasattr(response, 'current_program_scene_name'):
                    return response.current_program_scene_name
                elif hasattr(response, 'sceneName'):
                    return response.sceneName
                elif hasattr(response, 'name'):
                    return response.name
                elif hasattr(response, 'scene_name'):
                    return response.scene_name
                
                # 以下は辞書形式のレスポンス用
                if isinstance(response, dict):
                    if 'currentProgramSceneName' in response:
                        return response['currentProgramSceneName']
                    elif 'sceneName' in response:
                        return response['sceneName']
                    elif 'name' in response:
                        return response['name']
                    elif 'current_program_scene_name' in response:
                        return response['current_program_scene_name']
                    elif 'scene_name' in response:
                        return response['scene_name']
                
                # 上記の方法でシーン名が取得できない場合は、__dict__の内容をデバッグ出力
                if hasattr(response, '__dict__'):
                    print(f"応答の__dict__内容: {response.__dict__}")
                    for key, value in response.__dict__.items():
                        if isinstance(key, str) and ('scene' in key.lower() or 'name' in key.lower()):
                            print(f"候補キー '{key}' の値: {value}")
                            return value  # 最初の候補を返す
                
            except Exception as debug_e:
                print(f"レスポンス解析中のデバッグエラー: {debug_e}")
            
            # デバッグ情報
            print("現在のシーンを特定できません - 不明なレスポンス形式")
            print(f"レスポンスタイプ: {type(response)}")
            print(f"レスポンス属性: {dir(response)}")
            
            # dataclass_fieldsが存在するか確認
            if hasattr(response, '__dataclass_fields__'):
                print(f"データクラスフィールド: {response.__dataclass_fields__}")
            
            if hasattr(response, '__dict__'):
                print(f"レスポンス__dict__: {response.__dict__}")
                
                # もし辞書に'Scene'または'scene'を含むキーがあれば、そこから取得を試みる
                for key, value in response.__dict__.items():
                    if 'scene' in key.lower():
                        return value  # 最初に見つかったシーン関連の値を返す
            
            # 最終手段: ログからcurrent_program_scene_nameを特定して返す
            if hasattr(response, '__dict__') and 'current_program_scene_name' in str(response.__dict__):
                # 簡易的な解析
                for key, value in response.__dict__.items():
                    if isinstance(value, str) and 'Scene' in value:
                        return value
            
            return None
        except Exception as e:
            print(f"現在のシーン取得エラー: {str(e)}")
            return None
    
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