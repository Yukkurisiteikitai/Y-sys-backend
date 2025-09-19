# architecture/concrete_understanding/base.py
import uuid
from datetime import datetime
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from utils.yaml_load import load_yaml
from . import schema_architecture as schema
from ..abstract_recognition import schama_architecture as abstract_recognition_schema
from typing import List, Optional, Dict, Any
from pydantic import ValidationError

class ConcreteUnderstanding:
    """
    YourselfLMにおける「具象的理解」のためのアーキテクチャを実装するクラスです。
    過去の経験に基づいて状況を理解する対話的なプロセスを管理し、
    ユーザーのフィードバックによる洗練を可能にします。
    """
    def __init__(self, storage: RAGStorage, lm_client: Optional[LMStudioClient] = None):
        """
        ConcreteUnderstandingプロセスを初期化します。

        Args:
            storage: 経験を取得するためのRAGStorageインスタンス。
            lm_client: 言語モデル推論のためのLMStudioClientインスタンス。
                       Noneの場合、新しいクライアントが作成されます。
        """
        self.storage = storage
        self.lm = lm_client if lm_client else LMStudioClient()
        self.field_info: Optional[str] = None
        self.experience: Optional[List[Dict[str, Any]]] = None
        self.current_estimation: Optional[abstract_recognition_schema.abstract_recognition_response] = None
        self.history: List[Dict[str, Any]] = []

    def start_inference(self, field_info_input: str) -> Optional[abstract_recognition_schema.abstract_recognition_response]:
        """
        初期の状況情報を用いて推論プロセスを開始します。
        これには、RAGシステムのための高品質なクエリの作成、経験の検索と評価、
        そして推定の実行が含まれます。

        Args:
            field_info_input: 初期の状況や場面の情報。

        Returns:
            感情と思考の初期推定値。失敗した場合はNone。
        """
        self.field_info = field_info_input
        
        print("高品質なRAGクエリを作成中...")
        rag_query = self._create_rag_query(field_info_input)
        
        print("関連する経験を検索中...")
        retrieved_experiences = self.storage.search_similar(rag_query, category="experience", top_k=3)

        self.experience = self._evaluate_retrieved_experiences(retrieved_experiences, rag_query)
        
        print("初期推定を開始中...")
        self._run_estimation()
        
        return self.current_estimation

    def _create_rag_query(self, field_info_input: str) -> str:
        """
        入力された状況情報を分析し、時間、人物、環境などの要素を抽出して、
        RAGのための高品質なクエリを作成します。
        """
        prompt = f"""
        以下の状況説明文から、検索クエリとして利用するための重要な要素（時間、人物、環境）を抽出してください。
        そして、それらの要素を組み合わせた自然な文章の検索クエリを作成してください。

        状況説明文:
        「{field_info_input}」

        検索クエリ:
        """
        
        # LMを使用してクエリを生成します。
        generated_query = self.lm.generate_response(
            query=prompt,
            context="", # この部分には追加のコンテキストは不要
            model="gemma-3-1b-it"
        )
        
        print(f"生成されたRAGクエリ: {generated_query}")
        return generated_query

    def _evaluate_retrieved_experiences(self, experiences: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        検索された経験がクエリと関連性があるか評価します。
        （これは将来的な実装のためのプレースホルダーです）。
        """
        print("検索された経験の評価（現在はプレースホルダー）...")
        # 現時点では、経験をそのまま返します。
        # 将来的な実装では、LMを使用して関連性を評価したり、フィルタリングや要約を行ったりすることが考えられます。
        return experiences

    def _run_estimation(self, feedback: Optional[str] = None):
        """
        言語モデルを使用して推定を実行します。
        初期推定、またはフィードバックに基づく再推定に使用できます。
        """
        if feedback:
            # コンテキストには、前回の推定と新しいフィードバックが含まれます
            context_texts = f"""
            前回のコンテキスト:
              context_experience:{self.experience}
              context_field_info:{self.field_info}
            
            前回の推定:
              Emotion: {self.current_estimation.emotion_estimation if self.current_estimation else 'N/A'}
              Thought: {self.current_estimation.think_estimation if self.current_estimation else 'N/A'}

            ユーザーフィードバック:
              {feedback}
            """
            emotion_query = "ユーザーからのフィードバックを踏まえて、感情の動きを再予測してください。"
            think_query = "ユーザーからのフィードバックを踏まえて、思考を再予測してください。"
        else:
            # 初期コンテキスト
            context_texts = f"""
            コンテキスト:
              context_experience:{self.experience}
              context_field_info:{self.field_info}
            """
            emotion_query = "「context_field_info」に書かれている状況において「context_experience」のような体験をしてきた人はどのような感情の動きをするのかを予測してください。"
            think_query = "「context_field_info」に書かれている状況において「context_experience」のような体験をしてきた人はどのような思考をするのかを予測してくだい。"

        emostion_result: str = self.lm.generate_response(emotion_query, context_texts, "gemma-3-1b-it")
        think_result: str = self.lm.generate_response(think_query, context_texts, "gemma-3-1b-it")
        
        print("RAGの回答 (感情):\n", emostion_result)
        print("RAGの回答 (思考):\n", think_result)

        try:
            self.current_estimation = abstract_recognition_schema.abstract_recognition_response(
                emotion_estimation=emostion_result,
                think_estimation=think_result
            )
            self.history.append({"estimation": self.current_estimation, "feedback": feedback})
        except ValidationError as e:
            print(f"スキーマのバリデーションに失敗しました: {e}")
            # バリデーションエラーの場合、現在の推定は更新しませんが、
            # このイベントをログに記録すべきでしょう。
            self.history.append({"error": str(e), "feedback": feedback})

    def process_user_feedback(self, user_input: str) -> Optional[abstract_recognition_schema.abstract_recognition_response]:
        """
        ユーザーのフィードバックを処理し、状況を再評価して、更新された推定値を返します。
        このメソッドは現在、フィードバックを追加のコンテキストとして推定を再実行します。
        データベースに対するフィードバック評価のロジックはまだ実装されていません。

        Args:
            user_input: ユーザーから提供されたフィードバック。

        Returns:
            更新された推定値。失敗した場合はNone。
        """
        if not self.field_info or not self.experience:
            print("エラー: 推論が開始されていません。まず start_inference() を呼び出してください。")
            return None

        print(f"ユーザーフィードバックを処理中: {user_input}")
        
        # ここに、あなたのメモで言及されているように、feedback_dbやepisode_dbに対して
        # フィードバックを評価するロジックを追加します。
        # 現時点では、フィードバックを推定の洗練にのみ使用します。

        self.history[-1]["feedback"] = user_input
        self._run_estimation(feedback=user_input)
        
        return self.current_estimation

    def _create_episode_from_text(self, text: str, content_type: str, related_episode_id: Optional[str] = None) -> schema.EpisodeData:
        """
        (プレースホルダー) 自由記述テキストから詳細なEpisodeDataオブジェクトを生成します。
        将来的には、このメソッド内でLLMを使用して感情、キーワード、トピックなどを抽出します。
        """
        print(f"'{text}' から {content_type} のエピソードを生成中...")
        
        new_episode_id = str(uuid.uuid4())
        
        related_episodes = []
        if related_episode_id:
            related_episodes.append(schema.RelatedEpisode(episode_id=related_episode_id, relationship_type="is_response_to"))

        # 現在は基本的な情報のみを移入
        episode = schema.EpisodeData(
            episode_id=new_episode_id,
            thread_id="thread_placeholder", # TODO: スレッドIDを適切に管理する
            timestamp=datetime.now(),
            sequence_in_thread=0, # TODO: シーケンスを適切に管理する
            source_type="user_response_to_ai_prompt",
            author="user",
            content_type=content_type,
            text_content=text,
            status="active",
            sensitivity_level="medium", # デフォルト値
            related_episode_ids=related_episodes if related_episodes else None
            # AIによる解析情報はまだNone
        )
        return episode

    def start_thought_experiment(self, scenario_id: str, user_direct_answer: str, user_real_experience: str):
        """
        思考実験シナリオを実行し、2つの関連付けられたエピソードを生成します。
        
        Args:
            scenario_id: prompts/thought_experiments.yaml に定義されたシナリオのID。
            user_direct_answer: シナリオに対するユーザーの直接的な回答。
            user_real_experience: フォローアップ質問に対するユーザーの具体的な実体験。
        """
        print(f"思考実験シナリオ {scenario_id} を開始します。")
        
        # 1. シナリオライブラリを読み込む
        try:
            scenarios = load_yaml("prompts/thought_experiments.yaml")
            scenario = next((s for s in scenarios if s['id'] == scenario_id), None)
            if not scenario:
                print(f"エラー: シナリオID '{scenario_id}' が見つかりません。")
                return None, None
        except FileNotFoundError:
            print("エラー: prompts/thought_experiments.yaml が見つかりません。")
            return None, None

        print(f"シナリオ提示: {scenario['text']}")
        print(f"ユーザーの回答: {user_direct_answer}")

        # 2. 思考実験への直接的な回答から一つ目のエピソードを生成
        thought_episode = self._create_episode_from_text(
            text=user_direct_answer,
            content_type="value_articulation" # 指示通りcontent_typeで性質を区別
        )
        print(f"生成された思考エピソード (ID: {thought_episode.episode_id})")
        self.history.append({"episode": thought_episode.dict()})


        print(f"フォローアップ質問: {scenario['follow_up_question']}")
        print(f"ユーザーの実体験: {user_real_experience}")

        # 3. 実体験の語りから二つ目のエピソードを生成し、一つ目と関連付ける
        experience_episode = self._create_episode_from_text(
            text=user_real_experience,
            content_type="storytelling_personal_event", # 指示通りcontent_typeで性質を区別
            related_episode_id=thought_episode.episode_id # 指示通り関連付けを行う
        )
        print(f"生成された実体験エピソード (ID: {experience_episode.episode_id})")
        self.history.append({"episode": experience_episode.dict()})
        
        # 生成された2つのエピソードを返す
        return thought_episode, experience_episode


def architecture_base(storage: RAGStorage, field_info_input: str) -> Optional[abstract_recognition_schema.abstract_recognition_response]:
    # この関数は後方互換性のために維持されています。
    # 対話的なループなしで、一度だけの推定を実行します。
    process = ConcreteUnderstanding(storage)
    return process.start_inference(field_info_input)
