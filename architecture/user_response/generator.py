# architecture/user_response/generator.py
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
        あなたは、ユーザーの内面を深く洞察するAIアシスタントです。
        以下の入力情報を元に、「デフォルメ（抽象化）」と「具現化」の思考プロセスを経て、ユーザーの応答を生成してください。

        ## 思考プロセス
        1. **デフォルメ（抽象化）**: ユーザーの過去の経験（抽象的理解）から、今回の状況に共通する感情や思考のパターンを抽出します。これは物事の大きな括りを見つける作業です。
        2. **具現化（具体化）**: 抽象化されたパターンを、現在の具体的な状況（時間、場所、人間関係など）に当てはめて、より解像度の高い理解を形成します。不足している情報は積極的に推論・補完してください。
        3. **応答生成**: 上記の理解に基づき、「意思決定の推論」「行動の推論」「最終的な応答」の3つの要素を導き出してください。

        # 入力情報
        ## 1. ユーザーの現在の状況 (field_info)
        {field_info}

        ## 2. 抽象的理解 (過去の経験に基づく感情と思考の予測)
        - 予測される感情: {abstract_info.emotion_estimation}
        - 予測される思考: {abstract_info.think_estimation}

        ## 3. 具象的理解 (現在の状況を構造化したもの)
        - 出来事の内容: {concrete_info.text_content}
        - 出来事の種類: {concrete_info.content_type}
        - 関連する過去の出来事: {concrete_info.related_episode_ids}

        # 出力形式
        以下の形式で、3つの要素を明確に記述してください。
        DECISION: [ここに意思決定の推論を記述]
        ACTION: [ここに具体的な行動の推論を記述]
        RESPONSE: [ここにユーザーへの最終的な応答メッセージを記述]
        """

        prompt = "上記の指示と入力情報に従って、思考プロセスを実行し、指定された出力形式で応答を生成してください。"

        # LLMにリクエストを送信
        raw_response = self.lm.generate_response(
            query=prompt,
            context=context,
            model="gemma-3-1b-it" # or your preferred model
        )

        # LLMからの出力をパースしてスキーマに変換
        try:
            decision = "推論失敗"
            action = "推論失敗"
            final_response = raw_response # デフォルトはraw応答

            lines = raw_response.strip().split('\n')
            for line in lines:
                if line.startswith("DECISION:"):
                    decision = line.replace("DECISION:", "").strip()
                elif line.startswith("ACTION:"):
                    action = line.replace("ACTION:", "").strip()
                elif line.startswith("RESPONSE:"):
                    # RESPONSE:以降のすべての行を結合する
                    final_response = raw_response.split("RESPONSE:", 1)[1].strip()
                    break
            
            return UserResponse(
                inferred_decision=decision,
                inferred_action=action,
                final_response=final_response
            )

        except (IndexError, ValidationError) as e:
            print(f"応答のパースまたは検証に失敗しました: {e}")
            # フォールバックとして、raw応答全体を最終応答に入れる
            return UserResponse(
                inferred_decision="推論失敗",
                inferred_action="推論失敗",
                final_response=raw_response
            )
