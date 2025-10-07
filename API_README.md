# YourselfLM API 仕様書

## 概要

YourselfLMは、ユーザーの思考プロセスを段階的に解析し、ストリーミング形式で応答を返すAPIです。抽象的認識、具体的理解、思考プロセスの生成、最終応答の4つのフェーズを経て、ユーザーの感情状態や認知パターンに基づいた対話を実現します。

## ベースURL

```
http://127.0.0.1:8000
```

## 認証

現在のバージョンでは認証は実装されていません。

---

## エンドポイント

### 1. セッションの作成

新しいチャットセッションを開始します。

**エンドポイント:** `POST /api/v1/sessions`

**リクエストボディ:**

```json
{
  "user_id": "string (optional)",
  "metadata": {
    "client_info": "string",
    "任意のキー": "任意の値"
  }
}
```

**レスポンス:** `200 OK`

```json
{
  "session_id": "uuid",
  "thread_id": "uuid",
  "created_at": "2025-10-07T12:17:03.603545",
  "expires_at": "2025-10-08T12:17:03.603552"
}
```

**フィールド説明:**
- `session_id`: セッションの一意識別子
- `thread_id`: スレッドの一意識別子
- `created_at`: セッション作成日時（ISO 8601形式）
- `expires_at`: セッション有効期限（デフォルト24時間後）

---

### 2. メッセージ送信（ストリーミング）

ユーザーメッセージを送信し、ストリーミング形式で応答を受け取ります。

**エンドポイント:** `POST /api/v1/sessions/{session_id}/messages/stream`

**パスパラメータ:**
- `session_id`: セッションID（必須）

**ヘッダー:**
```
Accept: text/event-stream
```

**リクエストボディ:**

```json
{
  "message": "将来のキャリアについて悩んでいます。ゲーム開発に興味があるのですが、自分のスキルでやっていけるか不安です。",
  "sensitivity_level": "medium"
}
```

**フィールド説明:**
- `message`: ユーザーメッセージ（必須）
- `sensitivity_level`: 感度レベル（必須）- `"low"`, `"medium"`, `"high"` のいずれか

**レスポンス:** `200 OK` (Server-Sent Events)

ストリーミング形式で以下のイベントが順次送信されます：

#### イベント一覧

##### 1. フェーズ開始イベント
```
event: phase_start
data: {
  "phase": "abstract_recognition | concrete_understanding | response_generation",
  "timestamp": "2025-10-07T12:26:15.336870"
}
```

##### 2. 抽象的認識結果
```
event: abstract_result
data: {
  "emotional_state": ["不安", "焦り"],
  "cognitive_pattern": "将来への漠然とした不安",
  "value_alignment": ["autonomy", "growth"],
  "decision_context": "career_planning",
  "relevant_tags": ["self_improvement", "future_planning"],
  "confidence": 0.75
}
```

**フィールド説明:**
- `emotional_state`: 検出された感情状態のリスト
- `cognitive_pattern`: 認知パターンの概要
- `value_alignment`: 価値観の一致度を示すタグ
- `decision_context`: 意思決定のコンテキスト
- `relevant_tags`: 関連タグ
- `confidence`: 信頼度スコア（0.0-1.0）

##### 3. 具体的理解結果
```
event: concrete_links
data: {
  "related_episodes": [
    {
      "episode_id": "experience_2025-09-30T01:27:20Z",
      "text_snippet": "他人と意見が対立した場合は...",
      "relevance_score": 0.95,
      "tags": ["experience"],
      "source_metadata": null
    }
  ],
  "total_retrieved": 3
}
```

**フィールド説明:**
- `related_episodes`: 関連する過去の経験エピソードのリスト
  - `episode_id`: エピソードの一意識別子
  - `text_snippet`: エピソードのテキスト抜粋（最大150文字）
  - `relevance_score`: 関連度スコア（0.0-1.0）
  - `tags`: エピソードに付与されたタグ
  - `source_metadata`: ソースメタデータ（オプション）
- `total_retrieved`: 検索されたエピソードの総数

##### 4. 思考プロセス
```
event: thought_process
data: {
  "inferred_decision": "自分の考えを明確に定義する",
  "inferred_action": "スキルを具体的に棚卸しする",
  "key_considerations": [
    "emotional_trigger: 漠然とした不安感",
    "informational_input: 過去の経験から..."
  ],
  "emotional_tone": "neutral"
}
```

**フィールド説明:**
- `inferred_decision`: 推論された意思決定
- `inferred_action`: 推論された行動
- `key_considerations`: 重要な考慮事項のリスト
- `emotional_tone`: 感情のトーン

##### 5. 最終応答
```
event: final_response
data: {
  "message_id": "uuid",
  "response": {
    "nuance": "相手との対立を避けつつ...",
    "dialogue": "まず、自分のスキルを具体的に整理してみましょう。",
    "behavior": "PCを見つめる"
  },
  "metadata": {
    "total_processing_time_ms": 13286,
    "model_used": "gemma-3-1b-it",
    "safety_check": "passed"
  }
}
```

**フィールド説明:**
- `message_id`: メッセージの一意識別子
- `response`: 応答内容
  - `nuance`: ニュアンス・背景説明
  - `dialogue`: ユーザーへの対話メッセージ
  - `behavior`: 推測される行動
- `metadata`: メタデータ
  - `total_processing_time_ms`: 総処理時間（ミリ秒）
  - `model_used`: 使用されたモデル名
  - `safety_check`: 安全性チェック結果

##### 6. フェーズ完了イベント
```
event: phase_complete
data: {
  "phase": "abstract_recognition",
  "duration_ms": 8703.979
}
```

##### 7. ストリーム終了
```
event: stream_end
data: {
  "status": "complete",
  "timestamp": "2025-10-07T12:26:28.623660"
}
```

##### 8. エラーイベント
```
event: error
data: {
  "code": "INTERNAL_ERROR",
  "message": "エラーメッセージ",
  "timestamp": "2025-10-07T12:26:28.623660"
}
```

---

### 3. メッセージ履歴の取得

セッションのメッセージ履歴を取得します。

**エンドポイント:** `GET /api/v1/sessions/{session_id}/messages`

**パスパラメータ:**
- `session_id`: セッションID（必須）

**クエリパラメータ:**
- `limit`: 取得件数（デフォルト: 50）
- `offset`: オフセット（デフォルト: 0）
- `include_metadata`: メタデータを含めるか（デフォルト: false）

**レスポンス:** `200 OK`

```json
{
  "session_id": "uuid",
  "messages": [
    {
      "message_id": "uuid",
      "role": "user | assistant",
      "content": "メッセージ内容",
      "timestamp": "2025-10-07T12:17:03.603545"
    }
  ],
  "pagination": {
    "total": 100,
    "limit": 50,
    "offset": 0
  }
}
```

---

### 4. セッションの削除

セッションを削除します。

**エンドポイント:** `DELETE /api/v1/sessions/{session_id}`

**パスパラメータ:**
- `session_id`: セッションID（必須）

**レスポンス:** `204 No Content`

---

## エラーレスポンス

### 404 Not Found

セッションが見つからない場合：

```json
{
  "detail": "SESSION_NOT_FOUND"
}
```

セッションの有効期限が切れている場合：

```json
{
  "detail": "SESSION_EXPIRED"
}
```

### 500 Internal Server Error

サーバー内部エラー時は、ストリーミング中に`error`イベントが送信されます。

---

## 処理フロー

1. **Phase 1: Abstract Recognition（抽象的認識）**
   - ユーザーメッセージから感情状態と認知パターンを抽出
   - 所要時間: 約8-10秒

2. **Phase 2: Concrete Understanding（具体的理解）**
   - RAGシステムを使用して関連する過去の経験を検索
   - 所要時間: 約0.5秒

3. **Phase 3: Response Generation（応答生成）**
   - 思考プロセスを生成し、意思決定と行動を推論
   - 所要時間: 約4-5秒

4. **Phase 4: Final Response（最終応答）**
   - ユーザーへの対話メッセージを生成
   - 総処理時間: 約13-15秒

---

## 使用例

### Python クライアント例

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# 1. セッション作成
session_response = requests.post(
    f"{BASE_URL}/api/v1/sessions",
    json={"metadata": {"client_info": "test_client"}}
)
session_id = session_response.json()["session_id"]

# 2. メッセージ送信（ストリーミング）
message_payload = {
    "message": "将来のキャリアについて悩んでいます。",
    "sensitivity_level": "medium"
}

with requests.post(
    f"{BASE_URL}/api/v1/sessions/{session_id}/messages/stream",
    json=message_payload,
    headers={"Accept": "text/event-stream"},
    stream=True
) as r:
    for line in r.iter_lines(decode_unicode=True):
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data = json.loads(line[5:].strip())
            print(f"{event_name}: {data}")
```

---

## 技術スタック

- **フレームワーク**: FastAPI
- **ストリーミング**: SSE (Server-Sent Events) via sse-starlette
- **LLMモデル**: gemma-3-1b-it (LM Studio経由)
- **RAGストレージ**: ChromaDB
- **埋め込みモデル**: all-MiniLM-L6-v2

---

## 注意事項

1. セッションは24時間で自動的に有効期限切れとなります
2. ストリーミングレスポンスは順次送信されるため、クライアント側でイベントを逐次処理する必要があります
3. 現在のバージョンではメッセージ履歴の取得機能はダミー実装です
4. 並行リクエスト処理のため、ThreadPoolExecutor（最大100ワーカー）を使用しています

---

## バージョン

**API Version**: 1.0  
**最終更新日**: 2025年10月7日