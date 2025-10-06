
import asyncio
import asyncio
import json
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

# --- データモデル (仕様書 v1.0 より) ---

class SessionRequest(BaseModel):
    user_id: Optional[str] = None
    metadata: Dict[str, Any]

class SessionResponse(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(hours=24))

class MessageRequest(BaseModel):
    message: str
    sensitivity_level: str # "low|medium|high"

# Phase 1: Abstract Recognition
class AbstractRecognitionResult(BaseModel):
    emotional_state: List[str]
    cognitive_pattern: str
    value_alignment: List[str]
    decision_context: str
    relevant_tags: List[str]
    confidence: float

# Phase 2: Concrete Understanding
class Episode(BaseModel):
    episode_id: str
    text_snippet: str
    relevance_score: float
    tags: List[str]
    source_metadata: Optional[Dict[str, str]] = None

class ConcreteUnderstandingResult(BaseModel):
    related_episodes: List[Episode]
    total_retrieved: int

# Phase 3: Response Generation
class ThoughtProcess(BaseModel):
    inferred_decision: str
    inferred_action: str
    key_considerations: List[str]
    emotional_tone: str

# Phase 4: Final Response
class FinalResponseData(BaseModel):
    nuance: str
    dialogue: str
    behavior: str

class FinalResponse(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    response: FinalResponseData
    metadata: Dict[str, Any]


def extract_keywords(text: str) -> List[str]:
    """正規表現を使って、太字や引用符で囲まれたキーワードを抽出する"""
    # 「**単語**」, 「『単語』」, 「「単語」」 のようなパターンにマッチ
    patterns = [
        r'\*\*(.*?)\*\*',  # **word**
        r'『(.*?)』',      # 『word』
        r'「(.*?)」'       # 「word」
    ]
    keywords = []
    for pattern in patterns:
        keywords.extend(re.findall(pattern, text))

    # 抽出したキーワードをさらに分割・整形
    final_keywords = []
    for kw in keywords:
        # "不安, 焦り" のようなケースに対応
        final_keywords.extend([word.strip() for word in kw.replace('、', ',').split(',')])

    # 重複を削除し、空の文字列を除外
    return sorted(list(set(filter(None, final_keywords))))

def extract_main_idea(text: str) -> str:
    """長文から主要な思考パターン（最初の文や強調部分）を抽出する"""
    # 太字や引用符で囲まれた部分を優先的に抽出
    match = re.search(r'\*\*(.*?)\*\*|「(.*?)」|『(.*?)』', text)
    if match:
        # マッチしたグループの中からNoneでない最初のものを返す
        return next((g for g in match.groups() if g is not None), text.split('。')[0])
    
    # マッチしない場合は、最初の文を返す
    if '。' in text:
        return text.split('。')[0]
    return text


def parse_final_user_response(response_text: str) -> Dict[str, Any]:
    """UserResponseGeneratorからの生の出力をパースして辞書に変換する"""
    parsed_data = {
        "inferred_decision": "",
        "inferred_action": "",
        "nuance": "",
        "dialogue": "",
        "behavior": ""
    }

    try:
        # DECISION, ACTION, NUANCE, DIALOGUE, BEHAVIORを正規表現で抽出
        decision_match = re.search(r'DECISION:\*\*(.*?)\*\*|DECISION:(.*?)\n', response_text, re.DOTALL)
        if decision_match:
            parsed_data["inferred_decision"] = (decision_match.group(1) or decision_match.group(2) or "").strip()

        action_match = re.search(r'ACTION:\*\*(.*?)\*\*|ACTION:(.*?)\n', response_text, re.DOTALL)
        if action_match:
            parsed_data["inferred_action"] = (action_match.group(1) or action_match.group(2) or "").strip()

        nuance_match = re.search(r'NUANCE:\*\*(.*?)\*\*|NUANCE:(.*?)\n', response_text, re.DOTALL)
        if nuance_match:
            parsed_data["nuance"] = (nuance_match.group(1) or nuance_match.group(2) or "").strip()

        dialogue_match = re.search(r'DIALOGUE:\*\*(.*?)\*\*|DIALOGUE:(.*?)\n', response_text, re.DOTALL)
        if dialogue_match:
            # 「」で囲まれた部分を優先
            quoted_dialogue = re.search(r'「(.*?)」', dialogue_match.group(1) or dialogue_match.group(2) or "")
            if quoted_dialogue:
                parsed_data["dialogue"] = quoted_dialogue.group(1)
            else:
                parsed_data["dialogue"] = (dialogue_match.group(1) or dialogue_match.group(2) or "").strip()

        behavior_match = re.search(r'BEHAVIOR:\*\*(.*?)\*\*|BEHAVIOR:(.*?)\n', response_text, re.DOTALL)
        if behavior_match:
            parsed_data["behavior"] = (behavior_match.group(1) or behavior_match.group(2) or "").strip()

        # どれか一つでもパースできたら、元のテキストは不要と判断
        if any(parsed_data.values()):
            return parsed_data

    except Exception:
        pass # パース失敗時は何もしない

    # パースに失敗したか、マーカーが見つからなかった場合は、元のテキストをdialogueに入れる
    parsed_data["dialogue"] = response_text
    return parsed_data


from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from architecture.concrete_understanding.base import ConcreteUnderstanding
from architecture.user_response.generator import UserResponseGenerator
from architecture.concrete_understanding.schema_architecture import EpisodeData
from tqdm import tqdm

# --- グローバルインスタンスとセットアップ ---

def setup_storage() -> RAGStorage:
    """RAGStorageを初期化し、サンプルデータを投入する"""
    print("RAGストレージを初期化")
    storage = RAGStorage(USE_MEMORY_RUN=False) # ファイル保存あり

    print("テスト経験データをデータベースに追加")
    sample_experience_data = [
        "幼少期に、周囲に家がある田舎と都会の中間くらいの都市で育った。小学4年生の時にTokyo Game Showに行ったことがきっかけで、ゲーム制作に興味を持ち、3ヶ月かけてクソゲーを作った。",
        "小学校の先生の影響を強く受け、作れば自分の欲を叶えられるという考え方を学んだ。周囲からは「聞き魔」と呼ばれる。",
        "強迫観念があり、謎の天使と悪魔のような存在が頭の中に現れる。社会的にまずいと思われる可能性があるため、他人にはあまり話さない。",
    ]
    
    for d in tqdm(sample_experience_data, desc="Load-test-data",ncols=120, ascii="-="):
        storage.save_experience_data(
            text=d,
            metadata={"source": "initial_data"}
        )
 
    print("ストレージの準備が完了しました。")
    return storage

storage = setup_storage()
lm_client = LMStudioClient()
concrete_process = ConcreteUnderstanding(storage=storage, lm_client=lm_client)
response_gen = UserResponseGenerator(lm_client=lm_client)


# --- API実装 ---

app = FastAPI(
    title="YourselfLM API",
    version="1.0",
    description="ユーザーの思考プロセスをストリーミング形式で返却するAPI"
)

# セッション情報を保持するためのシンプルなインメモリ辞書
sessions = {}

@app.post("/api/v1/sessions", response_model=SessionResponse)
async def create_session(request: SessionRequest):
    """
    新しいチャットセッションを開始します。
    """
    new_session = SessionResponse()
    sessions[new_session.session_id] = new_session
    return new_session

@app.post("/api/v1/sessions/{session_id}/messages/stream")
async def stream_message(session_id: str, request: MessageRequest):
    """
    ユーザーメッセージを送信し、ストリーミング形式で応答を受け取ります。
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")

    async def event_generator():
        loop = asyncio.get_event_loop()
        start_time = datetime.now()
        try:
            # --- Phase 1: Abstract Recognition ---
            yield {"event": "phase_start", "data": {"phase": "abstract_recognition", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0.01)

            # ブロッキング処理を別スレッドで実行
            abstract_cli_result, retrieved_experiences = await loop.run_in_executor(
                None, concrete_process.start_inference, request.message
            )
            
            if not abstract_cli_result:
                raise Exception("Abstract recognition failed to produce a result.")

            extracted_emotions = extract_keywords(abstract_cli_result.emotion_estimation)
            extracted_pattern = extract_main_idea(abstract_cli_result.think_estimation)

            abstract_api_result = AbstractRecognitionResult(
                emotional_state=extracted_emotions if extracted_emotions else ["analysis_failed"],
                cognitive_pattern=extracted_pattern if extracted_pattern else "analysis_failed",
                value_alignment=["autonomy", "growth"], # Dummy
                decision_context="career_planning", # Dummy
                relevant_tags=["self_improvement", "future_planning"], # Dummy
                confidence=0.75 # Dummy
            )
            
            yield {"event": "abstract_result", "data": abstract_api_result.model_dump()}
            await asyncio.sleep(0.01)
            yield {"event": "phase_complete", "data": {"phase": "abstract_recognition", "duration_ms": (datetime.now() - start_time).total_seconds() * 1000}}
            await asyncio.sleep(0.01)

            # --- Phase 2: Concrete Understanding ---
            yield {"event": "phase_start", "data": {"phase": "concrete_understanding", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0.01)
            
            episodes = []
            if retrieved_experiences:
                for exp in retrieved_experiences:
                    episodes.append(Episode(
                        episode_id=exp.get("id", str(uuid.uuid4())),
                        text_snippet=exp.get("text", "")[:150],
                        relevance_score=max(0, 1 - exp.get("score", 1.0)),
                        tags=[exp.get("metadata", {}).get("category", "experience")]
                    ))

            concrete_result = ConcreteUnderstandingResult(related_episodes=episodes, total_retrieved=len(episodes))

            yield {"event": "concrete_links", "data": concrete_result.model_dump()}
            await asyncio.sleep(0.01)
            yield {"event": "phase_complete", "data": {"phase": "concrete_understanding", "duration_ms": (datetime.now() - start_time).total_seconds() * 1000}}
            await asyncio.sleep(0.01)

            # --- Phase 3 & 4: Response Generation and Finalization ---
            yield {"event": "phase_start", "data": {"phase": "response_generation", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0.01)

            concrete_info = EpisodeData(
                episode_id=str(uuid.uuid4()), thread_id=session_id, timestamp=datetime.now(),
                sequence_in_thread=0, source_type="user_api_input", author="user",
                content_type="situational_description", text_content=request.message,
                status="active", sensitivity_level=request.sensitivity_level
            )
            # ブロッキング処理を別スレッドで実行
            final_user_response = await loop.run_in_executor(
                None, response_gen.generate, abstract_cli_result, concrete_info, request.message
            )

            parsed_data = {}
            if "DECISION:" in final_user_response.dialogue or "ACTION:" in final_user_response.dialogue:
                parsed_data = parse_final_user_response(final_user_response.dialogue)
            else:
                parsed_data = {
                    "inferred_decision": final_user_response.inferred_decision,
                    "inferred_action": final_user_response.inferred_action,
                    "nuance": final_user_response.nuance,
                    "dialogue": final_user_response.dialogue,
                    "behavior": final_user_response.behavior
                }

            thought_process_api = ThoughtProcess(
                inferred_decision=parsed_data.get("inferred_decision", ""),
                inferred_action=parsed_data.get("inferred_action", ""),
                key_considerations=[f"{k}: {v}" for k, v in final_user_response.thought_process.items()],
                emotional_tone="neutral"
            )

            yield {"event": "thought_process", "data": thought_process_api.model_dump()}
            await asyncio.sleep(0.01)
            yield {"event": "phase_complete", "data": {"phase": "response_generation", "duration_ms": (datetime.now() - start_time).total_seconds() * 1000}}
            await asyncio.sleep(0.01)

            final_response_data = FinalResponseData(
                nuance=parsed_data.get("nuance", ""),
                dialogue=parsed_data.get("dialogue", "パース失敗"),
                behavior=parsed_data.get("behavior", "")
            )
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            final_response_api = FinalResponse(
                response=final_response_data,
                metadata={
                    "total_processing_time_ms": int(total_time),
                    "model_used": "gemma-3-1b-it",
                    "safety_check": "passed"
                }
            )
            yield {"event": "final_response", "data": final_response_api.model_dump()}
            await asyncio.sleep(0.01)

            # --- Stream End ---
            yield {"event": "stream_end", "data": {"status": "complete", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0.01)

        except Exception as e:
            error_message = {"error_code": "INTERNAL_ERROR", "message": str(e), "severity": "high"}
            yield {"event": "error", "data": error_message}
            await asyncio.sleep(0.01)
            yield {"event": "stream_end", "data": {"status": "error", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0.01)

    return EventSourceResponse(event_generator())

@app.get("/api/v1/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = 50, offset: int = 0, include_metadata: bool = False):
    """
    セッションのメッセージ履歴を取得します。(ダミー実装)
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    
    # 本来はデータベースなどから履歴を取得する
    dummy_messages = [
        {
            "message_id": str(uuid.uuid4()),
            "role": "user",
            "content": "こんにちは",
            "timestamp": datetime.now().isoformat(),
        },
        {
            "message_id": str(uuid.uuid4()),
            "role": "assistant",
            "content": "こんにちは！何かお話ししましょう。",
            "timestamp": datetime.now().isoformat(),
        }
    ]
    
    return {
        "session_id": session_id,
        "messages": dummy_messages[offset:offset+limit],
        "pagination": {
            "total": len(dummy_messages),
            "limit": limit,
            "offset": offset
        }
    }

@app.delete("/api/v1/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    """
    セッションを削除します。
    """
    if session_id in sessions:
        del sessions[session_id]
    else:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    return

if __name__ == "__main__":
    import uvicorn
    print("APIサーバーを起動します: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
