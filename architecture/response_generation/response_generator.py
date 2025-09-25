from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from ..abstract_recognition.base import artechture_base
from ..concrete_understanding.base import ConcreteUnderstanding
from .schema_response import UserResponse
from ..abstract_recognition.schama_architecture import abstract_recognition_response
from typing import Optional, List, Dict, Any

class ResponseGenerator:
    """
    ユーザーへの最終的な応答を生成するための統合的なクラス。
    抽象的理解と具体的理解を統合し、意思決定と行動を推論して応答を構築する。
    """
    def __init__(self, storage: RAGStorage, lm_client: Optional[LMStudioClient] = None):
        self.storage = storage
        self.lm = lm_client if lm_client else LMStudioClient()
        self.concrete_understanding_process = ConcreteUnderstanding(storage, self.lm)

    def generate_user_response(self, field_info_input: str) -> Optional[UserResponse]:
        """
        与えられた状況情報に基づいて、ユーザーへの応答を生成します。

        Args:
            field_info_input: 現在の状況や場面に関する情報。

        Returns:
            生成されたUserResponseオブジェクト、または失敗した場合はNone。
        """
        print("--- ユーザー応答生成プロセス開始 ---")

        # 1. 抽象的理解の取得
        print("抽象的理解を生成中...")
        abstract_understanding: Optional[abstract_recognition_response] = artechture_base(self.storage, field_info_input)
        if not abstract_understanding:
            print("エラー: 抽象的理解の生成に失敗しました。")
            return None
        print(f"抽象的理解 (感情): {abstract_understanding.emotion_estimation}")
        print(f"抽象的理解 (思考): {abstract_understanding.think_estimation}")

        # 2. 具体的理解の開始 (ConcreteUnderstandingクラスを使用)
        print("具体的理解を開始中...")
        # ConcreteUnderstandingのstart_inferenceはabstract_recognition_responseを返すため、
        # ここではその内部で管理されるfield_infoとexperienceを利用する
        self.concrete_understanding_process.start_inference(field_info_input)
        
        # 具体的理解の要約を生成
        concrete_understanding_summary = self._summarize_concrete_understanding(
            field_info_input,
            self.concrete_understanding_process.experience
        )
        print(f"具体的理解の要約: {concrete_understanding_summary}")

        # 3. 意思決定と行動の推論
        print("意思決定と行動を推論中...")
        inferred_decision, inferred_action = self._infer_decision_and_action(
            abstract_understanding,
            concrete_understanding_summary
        )
        print(f"推論された意思決定: {inferred_decision}")
        print(f"推論された行動: {inferred_action}")

        # 4. 最終的な応答テキストの生成
        print("最終的な応答テキストを生成中...")
        generated_response_text = self._generate_final_response_text(
            abstract_understanding,
            concrete_understanding_summary,
            inferred_decision,
            inferred_action
        )
        print(f"生成された応答テキスト: {generated_response_text}")

        # 5. UserResponseオブジェクトの構築
        try:
            user_response = UserResponse(
                abstract_understanding=abstract_understanding,
                concrete_understanding_summary=concrete_understanding_summary,
                inferred_decision=inferred_decision,
                inferred_action=inferred_action,
                generated_response_text=generated_response_text
            )
            print("--- ユーザー応答生成プロセス完了 ---")
            return user_response
        except Exception as e:
            print(f"エラー: UserResponseオブジェクトの構築に失敗しました: {e}")
            return None

    def _summarize_concrete_understanding(self, field_info: str, experiences: Optional[List[Dict[str, Any]]]) -> str:
        """
        具体的理解の要約を生成します。
        将来的にはLLMを使用してより高度な要約を行うことができます。
        """
        experience_summary = "関連する過去の経験はありません。"
        if experiences:
            # 経験のテキスト内容を結合して要約
            experience_texts = [exp.get("text_content", "") for exp in experiences if "text_content" in exp]
            if experience_texts:
                experience_summary = "関連する過去の経験: " + " ".join(experience_texts[:3]) + "..." # 最初の3つの経験を要約
            else:
                experience_summary = "関連する過去の経験はありますが、内容が抽出できませんでした。"

        return f"現在の状況: {field_info}。 {experience_summary}"

    def _infer_decision_and_action(self,
        abstract_understanding: abstract_recognition_response,
        concrete_understanding_summary: str
    ) -> (str, str):
        """
        抽象的理解と具体的理解に基づいて、意思決定と行動を推論します。
        """
        prompt = f"""
        以下の情報に基づいて、AIとしてどのような「意思決定」を行い、どのような「行動」を取るべきかを推論してください。

        抽象的理解:
        感情の推定: {abstract_understanding.emotion_estimation}
        思考の推定: {abstract_understanding.think_estimation}

        具体的理解の要約:
        {concrete_understanding_summary}

        意思決定:
        行動:
        """
        response = self.lm.generate_response(prompt, "", "gemma-3-1b-it")
        
        # レスポンスから意思決定と行動をパースする（簡易的な実装）
        decision = "不明な意思決定"
        action = "不明な行動"
        
        lines = response.split('\n')
        for line in lines:
            if line.startswith("意思決定:"):
                decision = line.replace("意思決定:", "").strip()
            elif line.startswith("行動:"):
                action = line.replace("行動:", "").strip()
        
        return decision, action

    def _generate_final_response_text(self,
        abstract_understanding: abstract_recognition_response,
        concrete_understanding_summary: str,
        inferred_decision: str,
        inferred_action: str
    ) -> str:
        """
        すべての推論結果を統合して、ユーザーへの最終的な応答テキストを生成します。
        """
        prompt = f"""
        以下の情報に基づいて、ユーザーに提示する自然で適切な応答テキストを生成してください。
        AIとしてのあなたの感情、思考、意思決定、行動を考慮し、共感的かつ建設的なトーンで記述してください。

        抽象的理解:
        感情の推定: {abstract_understanding.emotion_estimation}
        思考の推定: {abstract_understanding.think_estimation}

        具体的理解の要約:
        {concrete_understanding_summary}

        推論された意思決定:
        {inferred_decision}

        推論された行動:
        {inferred_action}

        ユーザーへの応答:
        """
        response_text = self.lm.generate_response(prompt, "", "gemma-3-1b-it")
        return response_text
