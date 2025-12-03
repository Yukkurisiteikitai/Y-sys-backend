"""
スキーマドキュメント：API応答・フロント通信仕様書

このファイルは、バックエンド→フロントエンドの全データフロー（スキーマ）を定義します。
Frontend開発者はこれを参考に、正しくデータを受け取ります。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json


# ===== PHASE 1: スレッド作成 =====
"""
POST /api/v1/threads
リクエスト:
{
  "user_id": "test-user",
  "title": "My Test Thread"
}

レスポンス (200):
{
  "thread_id": "uuid-xxxx",
  "user_id": "test-user",
  "title": "My Test Thread",
  "created_at": "2025-12-02T12:00:00Z"
}
"""


# ===== PHASE 2: ストリーミング応答 (SSE) =====
"""
POST /api/v1/threads/{thread_id}/messages/stream
リクエスト:
{
  "message": "新しいプロジェクトを提案されている状況",
  "sensitivity_level": "medium"
}

応答形式: Server-Sent Events (SSE)
各イベントはこのフォーマット:
  event: {event_name}
  data: {json_payload}
  
---

イベント 1: phase_start (初期化)
event: phase_start
data: {"phase": "abstract_recognition"}

イベント 2: abstract_result (抽象化結果)
event: abstract_result
data: {
  "phase": "abstract_recognition",
  "emotion_estimation": "期待と不安が混在",
  "think_estimation": "新しいことへの挑戦を考えている",
  "confidence": 0.87,
  "evidence": [
    {
      "id": "experience_id_123",
      "text": "過去に似た状況で",
      "score": 0.92
    }
  ]
}

イベント 3: phase_start (具象化)
event: phase_start
data: {"phase": "concrete_understanding"}

イベント 4: concrete_links (具象化結果)
event: concrete_links
data: {
  "phase": "concrete_understanding",
  "rag_query": "新しい状況での意思決定",
  "retrieved_experiences": [
    {
      "id": "exp_001",
      "text": "…",
      "relevance_score": 0.85
    }
  ],
  "current_estimation": {
    "emotion_estimation": "…",
    "think_estimation": "…"
  }
}

イベント 5: phase_start (応答生成)
event: phase_start
data: {"phase": "user_response_generation"}

イベント 6: thought_process (思考プロセス中間結果)
event: thought_process
data: {
  "phase": "user_response_generation",
  "inferred_decision": "挑戦してみることに決めた",
  "inferred_action": "準備を始める",
  "nuance": "少し不安な表情で",
  "dialogue": "「やってみます」",
  "behavior": "深く息を吸った",
  "confidence": 0.82,
  "evidence": {
    "answer": "複数視点の思考を統合…",
    "evidence": [ /* citation list */ ],
    "confidence": 0.85
  }
}

イベント 7: phase_complete (フェーズ完了)
event: phase_complete
data: {
  "phase": "user_response_generation",
  "status": "completed"
}

イベント 8: final_response (最終結果)
event: final_response
data: {
  "thread_id": "uuid-xxxx",
  "message_id": "msg_id_123",
  "user_response": {
    "thought_process": {
      "emotional_trigger": "新しい機会への期待",
      "informational_input": "過去の成功例",
      "thought_process_shift": "迷いながらも前進"
    },
    "inferred_decision": "挑戦する",
    "inferred_action": "準備を始める",
    "nuance": "少し不安だが、前向き",
    "dialogue": "「やってみます」",
    "behavior": "深く息を吸った"
  },
  "created_at": "2025-12-02T12:05:00Z"
}

イベント 9: stream_end (ストリーム終了)
event: stream_end
data: {"status": "completed"}

エラー時:
event: error
data: {
  "error_code": "INTERNAL_ERROR",
  "message": "Abstract recognition failed to produce a result.",
  "phase": "abstract_recognition"
}
"""


# ===== Python型定義 =====

@dataclass
class ThreadResponse:
    """スレッド作成時のレスポンス"""
    thread_id: str
    user_id: str
    title: str
    created_at: str


@dataclass
class PhaseStart:
    """フェーズ開始イベント"""
    phase: str  # "abstract_recognition", "concrete_understanding", "user_response_generation"


@dataclass
class AbstractResult:
    """抽象的理解の結果"""
    phase: str
    emotion_estimation: str
    think_estimation: str
    confidence: float
    evidence: List[Dict[str, Any]]


@dataclass
class ConcreteLinks:
    """具象的理解の結果"""
    phase: str
    rag_query: str
    retrieved_experiences: List[Dict[str, Any]]
    current_estimation: Dict[str, str]


@dataclass
class UserResponseGenerated:
    """ユーザー応答の生成結果"""
    phase: str
    inferred_decision: str
    inferred_action: str
    nuance: str
    dialogue: str
    behavior: str
    confidence: float
    evidence: Dict[str, Any]


@dataclass
class PhaseComplete:
    """フェーズ完了イベント"""
    phase: str
    status: str  # "completed"


@dataclass
class FinalResponse:
    """最終結果"""
    thread_id: str
    message_id: str
    user_response: Dict[str, Any]
    created_at: str


@dataclass
class StreamEnd:
    """ストリーム終了"""
    status: str  # "completed"


@dataclass
class ErrorEvent:
    """エラーイベント"""
    error_code: str
    message: str
    phase: str


# ===== Frontend処理の流れ =====
"""
## Frontend (JavaScript) での受け取り方

1. SSEパーサー を初期化
   const parser = new SSEParser(processEvent);

2. ストリーム受け取り
   for each line from response.body:
       parser.push(line);

3. processEvent(event, data) で処理
   - event: "phase_start", "abstract_result", etc.
   - data: JSON.parse(dataString)

4. UIの動的更新
   switch (event) {
       case "phase_start":
           phaseBox を作成、"Thinking..."を表示
       case "abstract_result":
           emotion/think を表示
       case "thought_process":
           decision/action/dialogue を表示
       case "final_response":
           チャット履歴に応答を追加
   }

## Frontendが知っておくべき点

- 各イベント は **独立したJSON** として送られる
  → ストリーミング中に部分的なデータが来ることはない
  
- evidence は複数の形式で来る可能性がある
  → リスト形式、またはネストされたDict形式
  
- confidence はバックエンドの信頼度を示す
  → 0.0 ~ 1.0 の float値
  
- error イベント来たらストリームを中断
  → ユーザーに"エラーが発生しました"と表示
"""


# ===== 使用例 =====

def example_frontend_code():
    """Frontend での実装例（疑似コード）"""
    code = """
    // SSE Parser (既存)
    class SSEParser {
        push(line) { /* ... */ }
    }
    
    // イベント処理
    const processEvent = (event, data) => {
        if (event === "phase_start") {
            // フェーズボックスを作成
            const phaseBox = document.createElement('div');
            phaseBox.id = `phase-${data.phase}`;
            phaseBox.textContent = formatPhaseName(data.phase);
            thinkingProcess.appendChild(phaseBox);
        }
        
        if (event === "abstract_result") {
            // 抽象的理解を表示
            const { emotion_estimation, think_estimation, confidence } = data;
            document.getElementById('emotion').textContent = emotion_estimation;
            document.getElementById('think').textContent = think_estimation;
            document.getElementById('confidence').textContent = `信頼度: ${(confidence * 100).toFixed(1)}%`;
        }
        
        if (event === "thought_process") {
            // ユーザー応答を表示
            const { inferred_decision, inferred_action, dialogue } = data;
            document.getElementById('decision').textContent = inferred_decision;
            document.getElementById('action').textContent = inferred_action;
            document.getElementById('dialogue').textContent = dialogue;
        }
        
        if (event === "final_response") {
            // チャット履歴に追加
            const { user_response } = data;
            appendMessage('assistant', formatResponse(user_response));
        }
        
        if (event === "error") {
            // エラー処理
            const { message } = data;
            appendMessage('assistant', `エラー: ${message}`);
        }
    };
    """
    return code


if __name__ == "__main__":
    print("=== API スキーマドキュメント ===")
    print(example_frontend_code())
