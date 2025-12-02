# システム起動とリクエスト処理のフロー

以下は本プロジェクトのバックエンド（`main_api.py` と `lm_studio_rag` クライアント周り）での処理順を示す Mermaid 図です。

## シーケンス図
```mermaid
sequenceDiagram
    participant Client as クライアント
    participant API as FastAPI (`main_api.py`)
    participant Router as Threads Router
    participant DI as 依存性注入
    participant Concrete as ConcreteUnderstanding
    participant ResponseGen as UserResponseGenerator
    participant Storage as RAGStorage (chroma_db / memory)
    participant LM as LMStudioClient
    participant LMServer as LM Studio (外部HTTP)

    Note over API,DI: アプリ初期化時
    API->>DI: Settings読み込み、インスタンス生成
    DI-->>API: 依存性を登録 (dependency_overrides)
    API->>Storage: (startup_event) sample_test_data.json 読込
    Storage-->>Storage: save_experience_data を複数回

    Note over Client,Router: リクエスト処理 (ランタイム)
    Client->>API: HTTP POST /api/v1/threads (クエリ/ユーザー入力)
    API->>Router: ルーティング
    Router->>DI: 依存性を取得 (storage, lm_client, concrete_process, response_gen)
    Router->>Concrete: ConcreteUnderstanding を実行 (前処理・検索・選別)
    Concrete->>Storage: 必要な文書を検索 / 追加保存
    Concrete->>LM: 分類や生成のために LM 呼び出し (chat/embed)
    LM->>LMServer: HTTP POST /v1/chat.completions or /v1/embeddings
    LMServer-->>LM: 応答 (生成テキスト or embedding)
    LM-->>Concrete: 応答受領
    Concrete-->>ResponseGen: 応答生成依頼（文脈を渡す）
    ResponseGen->>LM: 必要に応じて追加のLM呼び出し
    LM->>LMServer: chat 呼び出し
    LMServer-->>LM: レスポンス
    ResponseGen-->>Router: 最終レスポンスを返却
    Router-->>API: HTTPレスポンス作成（ストリーミング含む）
    API-->>Client: レスポンス送信
```

## フローチャート（高レベル）
```mermaid
flowchart TD
    A[Start: FastAPI 起動] --> B[Settings 読込]
    B --> C[依存性初期化
    (RAGStorage, LMStudioClient,
    ConcreteUnderstanding, ResponseGen)]
    C --> D{USE_MEMORY_STORAGE?}
    D -- Yes --> E[sample_test_data.json を読み込み
    Storage.save_experience_data で登録]
    D -- No --> F[外部 DB を使用]
    E --> G[Ready to accept requests]

    G --> H[Client -> POST /api/v1/threads]
    H --> I[Threads Router: 入力検証・依存性取得]
    I --> J[ConcreteUnderstanding: 検索・前処理]
    J --> K[Storage: 検索/保存]
    J --> L[LMStudioClient: embed/chat 呼び出し]
    L --> M[LM Studio サーバー: HTTP API]
    M --> L
    L --> N[Concrete/ResponseGen に生成結果を返す]
    N --> O[ResponseGen: 最終文章生成（必要ならLM再呼び出し）]
    O --> P[Router: レスポンス整形（ストリーミング）]
    P --> Q[Clientにレスポンス返却]
```

## 短い注釈
- **Startup**: `main_api.py` の `startup_event` がメモリストレージ用の初期データ読み込みを行う。
- **依存性注入**: `app.dependency_overrides[...] = lambda: ...` で実体を束ね、ルーターがこれを利用する。
- **RAGフロー**: ルーター → ConcreteUnderstanding（検索 + LM呼び出し）→ Storage／LM → ResponseGen → Client。
- **LM呼び出し**: `lm_studio_rag/lm_studio_client.py` が `/v1/chat/completions` と `/v1/embeddings` を使って外部LMにHTTPでアクセスする。

---
（必要なら `api/routers/threads` の詳細シーケンスも展開します。希望があれば教えてください）
```mermaid

```