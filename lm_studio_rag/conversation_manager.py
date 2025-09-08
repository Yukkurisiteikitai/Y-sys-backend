# conversation_manager.py
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from .utils import now_iso, save_json, load_json
from .lm_studio_client import LMStudioClient
from .classifier import ContentClassifier
from .storage import RAGStorage

logger = logging.getLogger("conversation")

@dataclass
class ConversationTurn:
    """単一の会話ターンを表すデータクラス"""
    turn_id: str
    user_message: str
    ai_response: str
    timestamp: str
    extracted_info: List[Dict[str, Any]]  # 抽出された人格・体験情報
    follow_up_questions: List[str]  # AIが生成したフォローアップ質問
    metadata: Dict[str, Any]

@dataclass
class ConversationThread:
    """会話スレッド全体を管理するデータクラス"""
    thread_id: str
    user_id: str
    title: str
    created_at: str
    last_updated: str
    turns: List[ConversationTurn]
    knowledge_gaps: List[Dict[str, Any]]  # 不足している情報のリスト
    metadata: Dict[str, Any]

class ConversationManager:
    """
    対話型RAG学習システムのメインマネージャー
    - スレッド形式での会話管理
    - 情報抽出と自動質問生成
    - RAGへの継続的な学習
    """
    
    def __init__(self, 
                 llm_client: LMStudioClient,
                 classifier: ContentClassifier,
                 storage: RAGStorage,
                 threads_db_path: str = "./threads.json"):
        self.llm = llm_client
        self.classifier = classifier
        self.storage = storage
        self.threads_db_path = threads_db_path
        self.threads = self._load_threads()
        
    def _load_threads(self) -> Dict[str, ConversationThread]:
        """スレッドデータを読み込み"""
        data = load_json(self.threads_db_path)
        threads = {}
        for thread_id, thread_data in data.items():
            # ConversationTurnオブジェクトを再構成
            turns = []
            for turn_data in thread_data.get('turns', []):
                turns.append(ConversationTurn(**turn_data))
            thread_data['turns'] = turns
            threads[thread_id] = ConversationThread(**thread_data)
        return threads
    
    def _save_threads(self):
        """スレッドデータを保存"""
        data = {}
        for thread_id, thread in self.threads.items():
            data[thread_id] = asdict(thread)
        save_json(self.threads_db_path, data)
    
    def create_thread(self, user_id: str, title: str = "") -> str:
        """新しい会話スレッドを作成"""
        thread_id = str(uuid.uuid4())
        thread = ConversationThread(
            thread_id=thread_id,
            user_id=user_id,
            title=title or f"会話 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_at=now_iso(),
            last_updated=now_iso(),
            turns=[],
            knowledge_gaps=[],
            metadata={}
        )
        self.threads[thread_id] = thread
        self._save_threads()
        return thread_id
    
    def extract_information_from_message(self, message: str) -> List[Dict[str, Any]]:
        """
        ユーザーメッセージから人格・体験情報を抽出
        LLMを使用してより高精度な抽出を行う
        """
        system_prompt = """
あなたは会話から人格情報と体験情報を抽出する専門家です。
以下のユーザーメッセージを分析し、抽出できる情報をJSON形式で返してください。

出力形式:
{
  "extracted_info": [
    {
      "text": "抽出したテキスト",
      "category": "personality" or "experience",
      "confidence": 0.0-1.0,
      "reasoning": "抽出理由"
    }
  ]
}

人格情報の例: 好み、性格、価値観、スキル、習慣など
体験情報の例: 過去の出来事、経験、行動、場所、時間など
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"メッセージ: {message}"}
        ]
        
        try:
            response = self.llm.chat(messages, temperature=0.1, max_tokens=500)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("extracted_info", [])
        except Exception as e:
            logger.error(f"情報抽出に失敗: {e}")
            return []
    
    def identify_knowledge_gaps(self, thread_id: str, current_query: str) -> List[Dict[str, Any]]:
        """
        現在の会話とRAGの内容を比較して、不足している情報を特定
        """
        thread = self.threads[thread_id]
        
        # 現在のクエリに対する関連情報を検索
        similar_personality = self.storage.search_similar(current_query, category="personality", top_k=5)
        similar_experience = self.storage.search_similar(current_query, category="experience", top_k=5)
        
        # 会話履歴の要約
        conversation_summary = self._summarize_conversation(thread)
        
        system_prompt = """
あなたは情報分析の専門家です。現在の質問と既存の関連情報、会話履歴を分析して、
より良い回答をするために不足している情報を特定してください。

出力形式:
{
  "knowledge_gaps": [
    {
      "gap_type": "personality" or "experience",
      "missing_info": "不足している情報の説明",
      "suggested_question": "ユーザーに聞くべき質問",
      "importance": 0.0-1.0,
      "reasoning": "なぜこの情報が必要なのか"
    }
  ]
}
"""
        
        context = f"""
現在の質問: {current_query}

関連する人格情報:
{json.dumps([{"text": item["text"], "score": item["score"]} for item in similar_personality], ensure_ascii=False, indent=2)}

関連する体験情報:
{json.dumps([{"text": item["text"], "score": item["score"]} for item in similar_experience], ensure_ascii=False, indent=2)}

会話履歴の要約:
{conversation_summary}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            response = self.llm.chat(messages, temperature=0.2, max_tokens=600)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("knowledge_gaps", [])
        except Exception as e:
            logger.error(f"情報不足の特定に失敗: {e}")
            return []
    
    def _summarize_conversation(self, thread: ConversationThread) -> str:
        """会話履歴を要約"""
        if not thread.turns:
            return "新しい会話です。"
        
        recent_turns = thread.turns[-5:]  # 最新5ターンのみ
        summary = []
        for turn in recent_turns:
            summary.append(f"ユーザー: {turn.user_message[:100]}")
            summary.append(f"AI: {turn.ai_response[:100]}")
        
        return "\n".join(summary)
    
    def generate_follow_up_questions(self, knowledge_gaps: List[Dict[str, Any]], max_questions: int = 2) -> List[str]:
        """
        知識の不足に基づいてフォローアップ質問を生成
        """
        # 重要度でソートして上位を選択
        sorted_gaps = sorted(knowledge_gaps, key=lambda x: x.get("importance", 0), reverse=True)
        top_gaps = sorted_gaps[:max_questions]
        
        questions = []
        for gap in top_gaps:
            if gap.get("suggested_question"):
                questions.append(gap["suggested_question"])
        
        return questions
    
    def process_message_and_respond(self, 
                                  thread_id: str, 
                                  user_message: str,
                                  auto_ask_followup: bool = True) -> Dict[str, Any]:
        """
        メインの処理フロー:
        1. ユーザーメッセージから情報抽出
        2. RAG検索で関連情報取得
        3. 情報不足を特定
        4. AI応答生成（必要に応じてフォローアップ質問含む）
        5. 抽出した情報をRAGに保存
        6. 会話履歴を更新
        """
        thread = self.threads[thread_id]
        
        # 1. 情報抽出
        extracted_info = self.extract_information_from_message(user_message)
        
        # 2. RAG検索
        similar_docs = self.storage.search_similar(user_message, top_k=5)
        context = "\n".join([f"- {doc['text']}" for doc in similar_docs])
        
        # 3. 情報不足の特定
        knowledge_gaps = self.identify_knowledge_gaps(thread_id, user_message)
        
        # 4. フォローアップ質問生成
        follow_up_questions = []
        if auto_ask_followup and knowledge_gaps:
            follow_up_questions = self.generate_follow_up_questions(knowledge_gaps)
        
        # 5. AI応答生成
        ai_response = self._generate_comprehensive_response(
            user_message, context, follow_up_questions, thread
        )
        
        # 6. 抽出した情報をRAGに保存
        for info in extracted_info:
            metadata = {
                "thread_id": thread_id,
                "turn_id": str(uuid.uuid4()),
                "confidence": info.get("confidence", 0.5),
                "source": "conversation_extraction",
                "reasoning": info.get("reasoning", "")
            }
            
            if info["category"] == "personality":
                self.storage.save_personality_data(info["text"], metadata)
            else:
                self.storage.save_experience_data(info["text"], metadata)
        
        # 7. 会話履歴更新
        turn = ConversationTurn(
            turn_id=str(uuid.uuid4()),
            user_message=user_message,
            ai_response=ai_response,
            timestamp=now_iso(),
            extracted_info=extracted_info,
            follow_up_questions=follow_up_questions,
            metadata={"knowledge_gaps": knowledge_gaps}
        )
        
        thread.turns.append(turn)
        thread.knowledge_gaps = knowledge_gaps
        thread.last_updated = now_iso()
        self._save_threads()
        
        return {
            "ai_response": ai_response,
            "extracted_info": extracted_info,
            "follow_up_questions": follow_up_questions,
            "knowledge_gaps": knowledge_gaps,
            "turn_id": turn.turn_id
        }
    
    def _generate_comprehensive_response(self, 
                                       user_message: str, 
                                       context: str, 
                                       follow_up_questions: List[str],
                                       thread: ConversationThread) -> str:
        """
        包括的なAI応答を生成（コンテキスト + フォローアップ質問含む）
        """
        system_prompt = f"""
あなたは親しみやすく知識豊富なAIアシスタントです。
ユーザーとの継続的な対話を通じて、より良いサポートを提供することが目標です。

会話履歴: {self._summarize_conversation(thread)}

回答の構成:
1. ユーザーの質問に対する直接的な回答
2. 関連する知識ベースの情報を活用
3. 必要に応じて自然な形でフォローアップ質問を含める

トーン: 親しみやすく、サポート的で、好奇心を示す
"""
        
        user_content = f"""
質問: {user_message}

関連情報:
{context if context else "関連する過去の情報は見つかりませんでした。"}

{f'追加で知りたいこと: {", ".join(follow_up_questions)}' if follow_up_questions else ''}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self.llm.chat(messages, temperature=0.7, max_tokens=800)
        return response["choices"][0]["message"]["content"]
    
    def get_thread_summary(self, thread_id: str) -> Dict[str, Any]:
        """スレッドの要約情報を取得"""
        thread = self.threads[thread_id]
        
        return {
            "thread_id": thread_id,
            "title": thread.title,
            "turn_count": len(thread.turns),
            "created_at": thread.created_at,
            "last_updated": thread.last_updated,
            "extracted_info_count": sum(len(turn.extracted_info) for turn in thread.turns),
            "current_knowledge_gaps": len(thread.knowledge_gaps)
        }
    
    def list_threads(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーのスレッド一覧を取得"""
        user_threads = [
            self.get_thread_summary(tid) 
            for tid, thread in self.threads.items() 
            if thread.user_id == user_id
        ]
        return sorted(user_threads, key=lambda x: x["last_updated"], reverse=True)


# enhanced_main.py - 使用例
from lm_studio_rag.lm_studio_client import LMStudioClient
from lm_studio_rag.classifier import ContentClassifier
from lm_studio_rag.storage import RAGStorage

def interactive_conversation_demo():
    """対話型のRAG学習デモ"""
    
    # 初期化
    llm = LMStudioClient()
    classifier = ContentClassifier(use_llm=False)
    storage = RAGStorage()
    
    # 基本サンプルで分類器を学習
    classifier.train_small_classifier({
        "personality": [
            "私は内向的な性格で、静かな環境を好みます",
            "コーヒーよりも紅茶派です",
            "数学が得意で論理的思考を重視します"
        ],
        "experience": [
            "昨日、新しいレストランに行きました",
            "大学時代にプログラミングを学んだ経験があります", 
            "先月の出張で面白い発見をしました"
        ]
    })
    
    conv_manager = ConversationManager(llm, classifier, storage)
    
    # 新しいスレッド作成
    user_id = "demo_user"
    thread_id = conv_manager.create_thread(user_id, "朝の習慣について")
    
    # 対話シミュレーション
    sample_messages = [
        "おはよう！朝の習慣について相談したいです",
        "最近朝起きるのが辛くて、もっと効率的な朝の過ごし方を知りたいです",
        "コーヒーを飲むのが日課です。でも時間がない時は紅茶にすることもあります",
        "週末は7時に起きますが、平日はギリギリまで寝てしまいます"
    ]
    
    for i, message in enumerate(sample_messages, 1):
        print(f"\n=== ターン {i} ===")
        print(f"ユーザー: {message}")
        
        result = conv_manager.process_message_and_respond(thread_id, message)
        
        print(f"AI: {result['ai_response']}")
        
        if result['extracted_info']:
            print("\n抽出された情報:")
            for info in result['extracted_info']:
                print(f"  - [{info['category']}] {info['text']} (信頼度: {info['confidence']:.2f})")
        
        if result['follow_up_questions']:
            print("\nフォローアップ質問:")
            for q in result['follow_up_questions']:
                print(f"  ? {q}")
        
        print("-" * 50)
    
    # スレッド要約表示
    summary = conv_manager.get_thread_summary(thread_id)
    print(f"\n会話要約:")
    print(f"ターン数: {summary['turn_count']}")
    print(f"抽出された情報数: {summary['extracted_info_count']}")
    print(f"現在の情報不足: {summary['current_knowledge_gaps']}件")

if __name__ == "__main__":
    interactive_conversation_demo()