import asyncio
import re
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Annotated

from fastapi import APIRouter, HTTPException, Request, Depends
from sse_starlette.sse import EventSourceResponse
from concurrent.futures import ThreadPoolExecutor

from api import schemas as api_schemas
from db import schemas as db_schemas
from db import crud
from dependencies import (
    DBSession, get_concrete_process, get_response_gen
)
from architecture.concrete_understanding.base import ConcreteUnderstanding
from architecture.user_response.generator import UserResponseGenerator
from architecture.concrete_understanding.schema_architecture import EpisodeData

# --- スレッドプール Executor ---
inference_executor = ThreadPoolExecutor(max_workers=100)

# --- Helper Functions ---
def extract_keywords(text: str) -> List[str]:
    patterns = [r'\*\*(.*?)\*\*', r'『(.*?)』', r'「(.*?)」']
    keywords = []
    for pattern in patterns:
        keywords.extend(re.findall(pattern, text))
    final_keywords = []
    for kw in keywords:
        final_keywords.extend([word.strip() for word in kw.replace('、', ',').split(',')])
    return sorted(list(set(filter(None, final_keywords))))

def extract_main_idea(text: str) -> str:
    match = re.search(r'\*\*(.*?)\*\*|「(.*?)」|『(.*?)』', text)
    if match:
        return next((g for g in match.groups() if g is not None), text.split('。')[0])
    if '。' in text:
        return text.split('。')[0]
    return text

def parse_final_user_response(response_text: str) -> Dict[str, Any]:
    parsed_data = {"inferred_decision": "", "inferred_action": "", "nuance": "", "dialogue": "", "behavior": ""}
    try:
        decision_match = re.search(r'DECISION:\*\*(.*?)\*\*|DECISION:(.*?)\\n', response_text, re.DOTALL)
        if decision_match:
            parsed_data["inferred_decision"] = (decision_match.group(1) or decision_match.group(2) or "").strip()
        action_match = re.search(r'ACTION:\*\*(.*?)\*\*|ACTION:(.*?)\\n', response_text, re.DOTALL)
        if action_match:
            parsed_data["inferred_action"] = (action_match.group(1) or action_match.group(2) or "").strip()
        nuance_match = re.search(r'NUANCE:\*\*(.*?)\*\*|NUANCE:(.*?)\\n', response_text, re.DOTALL)
        if nuance_match:
            parsed_data["nuance"] = (nuance_match.group(1) or nuance_match.group(2) or "").strip()
        dialogue_match = re.search(r'DIALOGUE:\*\*(.*?)\*\*|DIALOGUE:(.*?)\\n', response_text, re.DOTALL)
        if dialogue_match:
            quoted_dialogue = re.search(r'「(.*?)」', dialogue_match.group(1) or dialogue_match.group(2) or "")
            if quoted_dialogue:
                parsed_data["dialogue"] = quoted_dialogue.group(1)
            else:
                parsed_data["dialogue"] = (dialogue_match.group(1) or dialogue_match.group(2) or "").strip()
        behavior_match = re.search(r'BEHAVIOR:\*\*(.*?)\*\*|BEHAVIOR:(.*?)\\n', response_text, re.DOTALL)
        if behavior_match:
            parsed_data["behavior"] = (behavior_match.group(1) or behavior_match.group(2) or "").strip()
        if any(parsed_data.values()):
            return parsed_data
    except Exception:
        pass
    parsed_data["dialogue"] = response_text
    return parsed_data

# --- Router Definition ---
router = APIRouter()

@router.post("", response_model=api_schemas.ThreadResponse)
async def create_thread(
    thread_in: api_schemas.ThreadCreate,
    db: DBSession
):
    """Starts a new conversation thread and stores it in the database."""
    # TODO: In a real app, user_id should come from an auth token, not the request body.
    user = await crud.get_user(db, user_id=thread_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {thread_in.user_id} not found.")

    db_thread_in = db_schemas.ThreadCreate(
        mode="chat",
        title=thread_in.title
    )
    
    new_thread = await crud.create_thread(db=db, thread_data=db_thread_in, owner_user_id=thread_in.user_id)
    
    return api_schemas.ThreadResponse(
        thread_id=new_thread.id,
        user_id=new_thread.owner_user_id,
        title=new_thread.title,
        created_at=new_thread.timestamp
    )

@router.post("/{thread_id}/messages/stream") 
async def stream_message(
    thread_id: str, 
    message_req: api_schemas.MessageRequest, 
    http_request: Request,
    db: DBSession,
    concrete_process: Annotated[ConcreteUnderstanding, Depends(get_concrete_process)],
    response_gen: Annotated[UserResponseGenerator, Depends(get_response_gen)]
):
    """Streams a response to a message within a specific thread."""
    # Verify thread exists
    thread = await crud.get_thread(db, thread_id=thread_id) # [temp]まず書き込みがあるかのチャックをしている。でなかった場合は404が返ってくるここまではOK
    print(f"[test]:{type(thread)}") # [temp] こいつがまず本当にどんな情報をモテているのかを確認することを目標にまずは閲覧する。
    if not thread:
        raise HTTPException(status_code=404, detail="THREAD_NOT_FOUND")
    # [temp]特にエラーの進行はなし

    async def event_generator():
        loop = asyncio.get_running_loop()
        start_time = datetime.now()
        try:
            # The logic from the old stream_message endpoint goes here.
            # It is adapted to use thread_id instead of session_id.
            # Check if client already disconnected before starting heavy work
            if await http_request.is_disconnected():
                print(f"Client disconnected before abstract recognition: {thread_id}")
                return
            yield {"event": "phase_start", "data": {"phase": "abstract_recognition", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0)
            # run inference in threadpool
            abstract_cli_result, retrieved_experiences = await loop.run_in_executor(inference_executor, concrete_process.start_inference, message_req.message)
            # If client disconnected while inference was running, stop early
            if await http_request.is_disconnected():
                print(f"Client disconnected after abstract recognition: {thread_id}")
                return
            if not abstract_cli_result:
                raise Exception("Abstract recognition failed to produce a result.")
            abstract_api_result = api_schemas.AbstractRecognitionResult(
                emotional_state=extract_keywords(abstract_cli_result.emotion_estimation) or ["analysis_failed"],
                cognitive_pattern=extract_main_idea(abstract_cli_result.think_estimation) or "analysis_failed",
                value_alignment=["autonomy", "growth"],
                decision_context="career_planning",
                relevant_tags=["self_improvement", "future_planning"],
                confidence=0.75
            )
            yield {"event": "abstract_result", "data": abstract_api_result.model_dump()}
            await asyncio.sleep(0)
            yield {"event": "phase_complete", "data": {"phase": "abstract_recognition", "duration_ms": (datetime.now() - start_time).total_seconds() * 1000}}
            await asyncio.sleep(0)
            yield {"event": "phase_start", "data": {"phase": "concrete_understanding", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0)
            episodes = [
                api_schemas.Episode(
                    episode_id=exp.get("id", str(uuid.uuid4())),
                    text_snippet=exp.get("text", "")[:150],
                    relevance_score=max(0, 1 - exp.get("score", 1.0)),
                    tags=[exp.get("metadata", {}).get("category", "experience")]
                ) for exp in retrieved_experiences
            ] if retrieved_experiences else []
            concrete_result = api_schemas.ConcreteUnderstandingResult(related_episodes=episodes, total_retrieved=len(episodes))
            yield {"event": "concrete_links", "data": concrete_result.model_dump()}
            await asyncio.sleep(0)
            # check disconnection after sending concrete links
            if await http_request.is_disconnected():
                print(f"Client disconnected after concrete links: {thread_id}")
                return
            yield {"event": "phase_complete", "data": {"phase": "concrete_understanding", "duration_ms": (datetime.now() - start_time).total_seconds() * 1000}}
            await asyncio.sleep(0)
            yield {"event": "phase_start", "data": {"phase": "response_generation", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0)
            # prepare episode data
            concrete_info = EpisodeData(
                episode_id=str(uuid.uuid4()), thread_id=thread_id, timestamp=datetime.now(),
                sequence_in_thread=0, source_type="user_api_input", author="user",
                content_type="situational_description", text_content=message_req.message,
                status="active", sensitivity_level=message_req.sensitivity_level
            )
            # check disconnection before starting response generation
            if await http_request.is_disconnected():
                print(f"Client disconnected before response generation: {thread_id}")
                return
            final_user_response = await loop.run_in_executor(inference_executor, response_gen.generate, abstract_cli_result, concrete_info, message_req.message)
            parsed_data = parse_final_user_response(final_user_response.dialogue) if "DECISION:" in final_user_response.dialogue or "ACTION:" in final_user_response.dialogue else {
                "inferred_decision": final_user_response.inferred_decision,
                "inferred_action": final_user_response.inferred_action,
                "nuance": final_user_response.nuance,
                "dialogue": final_user_response.dialogue,
                "behavior": final_user_response.behavior
            }
            thought_process_api = api_schemas.ThoughtProcess(
                inferred_decision=parsed_data.get("inferred_decision", ""),
                inferred_action=parsed_data.get("inferred_action", ""),
                key_considerations=[f"{k}: {v}" for k, v in final_user_response.thought_process.items()],
                emotional_tone="neutral"
            )
            yield {"event": "thought_process", "data": thought_process_api.model_dump()}
            await asyncio.sleep(0)
            yield {"event": "phase_complete", "data": {"phase": "response_generation", "duration_ms": (datetime.now() - start_time).total_seconds() * 1000}}
            await asyncio.sleep(0)
            final_response_data = api_schemas.FinalResponseData(
                nuance=parsed_data.get("nuance", ""),
                dialogue=parsed_data.get("dialogue", "パース失敗"),
                behavior=parsed_data.get("behavior", "")
            )
            final_response_api = api_schemas.FinalResponse(
                response=final_response_data,
                metadata={
                    "total_processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                    "model_used": "gemma-3-1b-it",
                    "safety_check": "passed"
                }
            )
            yield {"event": "final_response", "data": final_response_api.model_dump()}
            await asyncio.sleep(0)
            yield {"event": "stream_end", "data": {"status": "complete", "timestamp": datetime.now().isoformat()}}
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            # Client likely disconnected; end silently
            print(f"Stream cancelled (likely client disconnect) for thread: {thread_id}")
            return
        except Exception as e:
            # If client disconnected, avoid sending internal error events
            try:
                if await http_request.is_disconnected():
                    print(f"Client disconnected during error for thread: {thread_id}: {e}")
                    return
            except Exception:
                # If checking disconnection fails, continue to send error event
                pass
            error_data = {"code": "INTERNAL_ERROR", "message": str(e), "timestamp": datetime.now().isoformat()}
            yield {"event": "error", "data": error_data, "retry": 10000}
            yield {"event": "stream_end", "data": {"status": "error", "timestamp": datetime.now().isoformat()}}
    return EventSourceResponse(event_generator())
