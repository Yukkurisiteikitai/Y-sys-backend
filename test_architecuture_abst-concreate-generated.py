# run_full_process.py

import os
from typing import Optional

# --- 必要なコンポーネントをインポート ---
# (プロジェクトのディレクトリ構造に合わせてパスを調整してください)
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from lm_studio_rag.classifier import ContentClassifier
from architecture.abstract_recognition import base as arh_abstract
from architecture.concrete_understanding.base import ConcreteUnderstanding
from architecture.response_generation.response_generator import ResponseGenerator
from architecture.response_generation.schema_response import UserResponse

# --- 1. 初期設定と準備 ---

def initialize_components():
    """テストに必要なコンポーネントを初期化して返す"""
    print("--- 1. コンポーネントの初期化を開始 ---")
    
    # インメモリで動作するストレージを初期化
    storage = RAGStorage(USE_MEMORY_RUN=True)
    print("RAGStorage (インメモリ) を初期化しました。")
    
    # LM Studioクライアントを初期化
    lm_client = LMStudioClient()
    print("LMStudioClient を初期化しました。")
    
    # コンテンツ分類器を初期化・訓練
    classifier = ContentClassifier(use_llm=False)
    classifier.train_small_classifier({
        "personality": ["私は内向的です", "論理的思考を重視します"],
        "experience": ["昨日、新しいレストランに行きました", "大学でプログラミングを学びました"]
    })
    print("ContentClassifier を訓練しました。")
    
    print("--- コンポーネントの初期化が完了 ---\n")
    return storage, lm_client, classifier

# --- 2. サンプルデータの保存 ---

def populate_initial_data(storage: RAGStorage, classifier: ContentClassifier):
    """RAGで利用するための初期データをストレージに保存する"""
    print("--- 2. 初期データの保存を開始 ---")
    
    initial_data = [
        "コーヒーよりも紅茶派です", # personality
        "先月の出張で面白い発見をしました", # experience
        "静かな環境を好みます", # personality
        "チームでのプロジェクト管理の経験があります" # experience
    ]
    
    for text in initial_data:
        res = classifier.classify(text)
        label = res.get("label", "unknown")
        print(f"分類: '{text}' -> {label}")
        if label == "personality":
            storage.save_personality_data(text, {"source": "initial_data"})
        else:
            storage.save_experience_data(text, {"source": "initial_data"})
            
    print(f"合計 {len(initial_data)} 件の初期データを保存しました。")
    print("--- 初期データの保存が完了 ---\n")

# --- 3. 思考実験の実行とデータ保存 ---

def run_and_save_thought_experiment(storage: RAGStorage, lm_client: LMStudioClient):
    """思考実験を実行し、その結果をストレージに保存する"""
    print("--- 3. 思考実験の実行を開始 ---")
    
    understanding_process = ConcreteUnderstanding(storage, lm_client)
    
    # prompts/thought_experiments.yaml に定義されているシナリオIDを指定
    scenario_id = "trolley_problem_001" 
    user_direct_answer = "何もしない。1人を助けるために5人を犠牲にする積極的な介入はできない。"
    user_real_experience = "過去に、チームの意見が割れた際、自分が何もしなかったことで、結果的に多数派の意見が通り、少数派のメンバーが不満を抱えたことがあった。自分の不作為が結果に影響を与えることを痛感した。"
    
    print(f"シナリオ '{scenario_id}' を実行します。")
    thought_episode, experience_episode = understanding_process.start_thought_experiment(
        scenario_id=scenario_id,
        user_direct_answer=user_direct_answer,
        user_real_experience=user_real_experience
    )
    
    if thought_episode and experience_episode:
        print("思考実験の回答と関連する実体験をストレージに保存しました。")
    else:
        print("エラー: 思考実験のデータ保存に失敗しました。")
        
    print("--- 思考実験の実行が完了 ---\n")


# --- 4. メインの応答生成プロセスの実行 ---

def execute_full_response_generation(storage: RAGStorage, lm_client: LMStudioClient):
    """
    全てのコンポーネントを連携させ、最終的なユーザー応答を生成するプロセスを実行する。
    """
    print("--- 4. 統合応答生成プロセスを開始 ---")
    
    # ResponseGeneratorをインスタンス化
    response_generator = ResponseGenerator(storage, lm_client)
    
    # 応答生成のトリガーとなる場面情報を定義
    field_info_input = """
{
  "field_info": {
    "field_env": {
      "time": "afternoon",
      "weather": "rainy",
      "location": "a tense meeting room"
    },
    "human_env": [
      {
        "nam": "Mr. Yamada (Project Manager)",
        "feel": "frustrated",
        "state": "looking at a delayed project schedule"
      },
      {
        "nam": "Ms. Sato (Lead Developer)",
        "feel": "anxious",
        "state": "explaining a technical issue that caused the delay"
      },
      {
        "nam": "You (AI Assistant)",
        "feel": "neutral",
        "state": "observing the situation to provide support"
      }
    ]
  }
}
    """
    print("以下の場面状況に基づいて応答を生成します:")
    print(field_info_input)
    
    # 応答生成メソッドを実行
    user_response: Optional[UserResponse] = response_generator.generate_user_response(field_info_input)
    
    # --- 結果の表示 ---
    print("\n--- 最終生成結果 ---")
    if user_response:
        print("\n[抽象的理解]")
        print(f"  感情の推定: {user_response.abstract_understanding.emotion_estimation}")
        print(f"  思考の推定: {user_response.abstract_understanding.think_estimation}")
        
        print("\n[具体的理解の要約]")
        print(f"  {user_response.concrete_understanding_summary}")
        
        print("\n[推論された意思決定と行動]")
        print(f"  意思決定: {user_response.inferred_decision}")
        print(f"  行動: {user_response.inferred_action}")
        
        print("\n[最終的なユーザーへの応答テキスト]")
        print("----------------------------------------")
        print(user_response.generated_response_text)
        print("----------------------------------------")
    else:
        print("応答の生成に失敗しました。")
        
    print("\n--- 統合応答生成プロセスが完了 ---")


if __name__ == "__main__":
    print("========== 全体実行プロセスを開始します ==========\n")
    
    # 各ステップを順番に実行
    storage, lm_client, classifier = initialize_components()
    populate_initial_data(storage, classifier)
    run_and_save_thought_experiment(storage, lm_client)
    execute_full_response_generation(storage, lm_client)
    
    print("\n========== 全体実行プロセスが正常に終了しました ==========")