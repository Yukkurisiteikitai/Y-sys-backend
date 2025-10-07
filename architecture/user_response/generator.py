# architecture/user_response/generator.py
import re
from lm_studio_rag.lm_studio_client import LMStudioClient
from .schema import UserResponse
from ..abstract_recognition.schama_architecture import abstract_recognition_response
from ..concrete_understanding.schema_architecture import EpisodeData
from pydantic import ValidationError

class UserResponseGenerator:
    """
    抽象的理解（デフォルメ）と具象的理解（具現化）を統合し、
    ユーザーの意思決定、行動、そして最終的な応答を推論するクラス。
    """
    def __init__(self, lm_client: LMStudioClient = None):
        self.lm = lm_client if lm_client else LMStudioClient()

    def generate(
        self,
        abstract_info: abstract_recognition_response,
        concrete_info: EpisodeData, # concrete_understandingからの出力
        field_info: str
    ) -> UserResponse:
        """
        与えられた抽象的・具象的情報から、最終的なユーザー応答を生成します。
        """
        context = f"""
        # 指示
        あなたは、これから与えられる情報を持つ「人物そのもの」です。
        あなた自身の過去の経験（抽象的理解）と、現在の具体的な状況（具象的理解）に基づいて、あたかもあなたがその人物であるかのように、一人称視点（「私」）で思考し、応答してください。
        物語的、比喩的、詩的な表現は絶対に使用しないでください。

        # 入力情報
        ## 1. ユーザーの現在の状況 (field_info)
        {field_info}

        ## 2. 抽象的理解 (過去の経験に基づく感情と思考の予測)
        - 予測される感情: {abstract_info.emotion_estimation}
        - 予測される思考: {abstract_info.think_estimation}

        # 出力形式
        以下のフォーマットに厳密に従って、思考プロセスと最終出力を記述してください。

        --- 思考プロセス ---
        - **感情的トリガー (Emotional Trigger):** (あなたの応答の根底にある感情的要因を記述)
        - **情報的インプット (Informational Input):** (過去の経験や現在の状況など、意思決定に利用した情報を記述)
        - **思考の変遷 (Thought Process Shift):** (感情と情報がどのように組み合わさり、最終的な意思決定に至ったかの思考の流れを記述)

        --- 最終出力 ---
        - **DECISION:** (私がどう考え、決断したかを記述)
        - **ACTION:** (私が次に行う具体的な行動を記述)
        - **NUANCE:** (応答の際の、観察可能な非言語的な態度や雰囲気を簡潔に記述。例:「少し考え込むように」「静かに頷き」)
        - **DIALOGUE:** (ユーザーへの発話内容のみを「」で括って記述。地の文は含めない)
        - **BEHAVIOR:** (発話に伴う、客観的に観測可能な物理的行動を記述。例:「PCに向き直り、キーボードを叩き始めた」)
        """

        prompt = "上記の指示と入力情報に従って、思考プロセスを実行し、指定された出力形式で応答を生成してください。"

        raw_response = self.lm.generate_response(
            query=prompt,
            context=context,
            model="gemma-3-1b-it"
        )
        print(f"「LLMの回答」@@@\n{raw_response}\n@@@")

        try:
            # --- 最終版・堅牢なパース戦略 ---
            # 1. 応答全体から「キー: 値」のペアをすべて抽出する
            #    キーに日本語など任意の文字が含まれることを許容する `([^\n:]+?)` を使用
            pattern = r"(?im)^\s*[-*]*\s*([^\n:]+?)\s*[-*]*\s*:\s*(.*)"
            matches = re.findall(pattern, raw_response)
            
            all_data = {key.strip(): value.strip() for key, value in matches}

            if not all_data:
                raise ValueError("応答からキーと値のペアを一つも抽出できませんでした。")

            # 2. 抽出したデータからUserResponseのフィールドを埋める
            thought_dict = {}
            key_mapping = {
                '感情的トリガー': 'emotional_trigger',
                '情報的インプット': 'informational_input',
                '思考の変遷': 'thought_process_shift'
            }
            # 英語キーも直接マッピング
            direct_mapping = {
                'DECISION': 'inferred_decision',
                'ACTION': 'inferred_action',
                'NUANCE': 'nuance',
                'DIALOGUE': 'dialogue',
                'BEHAVIOR': 'behavior'
            }

            # 最終的にUserResponseに渡すデータを準備
            parsed_data = {
                'thought_process': {},
                'inferred_decision': '推論失敗',
                'inferred_action': '推論失敗',
                'nuance': '',
                'dialogue': '',
                'behavior': ''
            }

            for key, value in all_data.items():
                # まず日本語キーで検索
                found = False
                for jp, en in key_mapping.items():
                    if jp in key:
                        parsed_data['thought_process'][en] = value
                        found = True
                        break
                if found: continue

                # 次に英語キーで検索
                for en_key, field_name in direct_mapping.items():
                    if en_key in key:
                        # NUANCEは特別処理
                        if field_name == 'nuance':
                            parsed_data[field_name] = re.split(r'[。\n]', value)[0]
                        # DIALOGUEは特別処理
                        elif field_name == 'dialogue':
                            parsed_data[field_name] = value.strip('「」')
                        else:
                            parsed_data[field_name] = value
                        break

            return UserResponse(**parsed_data)

        except (IndexError, ValidationError, ValueError) as e:
            print(f"応答のパースまたは検証に失敗しました: {e}")
            return UserResponse(dialogue=raw_response)
