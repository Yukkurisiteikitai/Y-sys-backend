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

        # 4. 構造化された応答の生成
        print("構造化された応答を生成中...")
        structured_response = self._generate_structured_response(
            abstract_understanding,
            concrete_understanding_summary,
            inferred_decision,
            inferred_action
        )
        print(f"生成された構造化応答: {structured_response}")

        # 5. UserResponseオブジェクトの構築
        try:
            user_response = UserResponse(
                abstract_understanding=abstract_understanding,
                concrete_understanding_summary=concrete_understanding_summary,
                inferred_decision=inferred_decision,
                inferred_action=inferred_action,
                thought_process=structured_response.get('thought_process', {}),
                nuance=structured_response.get('nuance', ''),
                dialogue=structured_response.get('dialogue', ''),
                behavior=structured_response.get('behavior', '')
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

    def _generate_structured_response(self,
        abstract_understanding: abstract_recognition_response,
        concrete_understanding_summary: str,
        inferred_decision: str,
        inferred_action: str
    ) -> Dict[str, Any]:
        """
        すべての推論結果を統合し、構造化された応答（思考プロセス、ニュアンス、セリフ、行動）を生成します。
        """
        prompt = f"""
        あなたは、ユーザーの状況を深く理解し、内省を促す応答を生成するAIです。
        以下の情報に基づいて、あなたの思考プロセスと最終的な出力を厳格なフォーマットで生成してください。

        # 入力情報
        ## 抽象的理解
        - 感情の推定: {abstract_understanding.emotion_estimation}
        - 思考の推定: {abstract_understanding.think_estimation}

        ## 具体的理解の要約
        {concrete_understanding_summary}

        ## 推論された意思決定と行動
        - 意思決定: {inferred_decision}
        - 行動: {inferred_action}

        # 出力フォーマット
        以下のフォーマットに厳密に従って、思考プロセスと最終出力を記述してください。
        物語的、比喩的、詩的な表現は絶対に使用しないでください。

        --- 思考プロセス ---
        - **感情的トリガー (Emotional Trigger):** (あなたの応答の根底にある感情的要因を記述)
        - **情報的インプット (Informational Input):** (過去の経験や現在の状況など、意思決定に利用した情報を記述)
        - **思考の変遷 (Thought Process Shift):** (感情と情報がどのように組み合わさり、最終的な意思決定に至ったかの思考の流れを記述)

        --- 最終出力 ---
        - **NUANCE:** (応答の際の、観察可能な非言語的な態度や雰囲気を簡潔に記述。例:「少し考え込むように」「静かに頷き」)
        - **DIALOGUE:** (ユーザーへの発話内容のみを「」で括って記述。地の文は含めない)
        - **BEHAVIOR:** (発話に伴う、客観的に観測可能な物理的行動を記述。例:「PCに向き直り、キーボードを叩き始めた」)
        """
        response_text = self.lm.generate_response(prompt, "", "gemma-3-1b-it")

        # レスポンスをパースして辞書に格納
        parsed_response = {
            "thought_process": {},
            "nuance": "",
            "dialogue": "",
            "behavior": ""
        }

        current_section = None
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('--- 思考プロセス ---'):
                current_section = 'thought'
                continue
            elif line.startswith('--- 最終出力 ---'):
                current_section = 'output'
                continue

            if current_section == 'thought':
                if line.startswith('- **感情的トリガー (Emotional Trigger):**'):
                    parsed_response["thought_process"]['emotional_trigger'] = line.replace('- **感情的トリガー (Emotional Trigger):**', '').strip()
                elif line.startswith('- **情報的インプット (Informational Input):**'):
                    parsed_response["thought_process"]['informational_input'] = line.replace('- **情報的インプット (Informational Input):**', '').strip()
                elif line.startswith('- **思考の変遷 (Thought Process Shift):**'):
                    parsed_response["thought_process"]['thought_process_shift'] = line.replace('- **思考の変遷 (Thought Process Shift):**', '').strip()
            
            elif current_section == 'output':
                if line.startswith('- **NUANCE:**'):
                    parsed_response['nuance'] = line.replace('- **NUANCE:**', '').strip()
                elif line.startswith('- **DIALOGUE:**'):
                    parsed_response['dialogue'] = line.replace('- **DIALOGUE:**', '').strip()
                elif line.startswith('- **BEHAVIOR:**'):
                    parsed_response['behavior'] = line.replace('- **BEHAVIOR:**', '').strip()

        return parsed_response
