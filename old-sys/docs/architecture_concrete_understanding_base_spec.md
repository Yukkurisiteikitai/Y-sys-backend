# `architecture/concrete_understanding/base.py` 仕様書

## 1. 概要

このファイルは、YourselfLMアーキテクチャにおける「具象的理解（Concrete Understanding）」のロジックを実装します。

主な責務は以下の通りです。
- ユーザーから与えられた特定の状況（`field_info`）をインプットとして受け取ります。
- RAG (Retrieval-Augmented Generation) を用いて、その状況に関連する過去の経験（`experience`）を検索します。
- 状況と過去の経験を元に、言語モデル（LLM）を使ってユーザーの感情（`emotion`）と思考（`think`）を推定します。
- ユーザーからのフィードバックを受け取り、推定をさらに洗練させる対話的なプロセスを管理します。

## 2. クラス定義

### `ConcreteUnderstanding`

#### 2.1. 説明

具象的理解のプロセス全体を管理する主要なクラスです。インスタンス化され、対話のセッションを通じて状態を保持します。

#### 2.2. 属性

- `storage` (`RAGStorage`): 経験の検索と保存を行うためのストレージインスタンス。
- `lm` (`LMStudioClient`): 言語モデルとの対話を行うためのクライアントインスタンス。
- `field_info` (`Optional[str]`): 現在処理中のユーザーの状況説明。
- `experience` (`Optional[List[Dict[str, Any]]]`): RAGによって検索された関連する過去の経験のリスト。
- `current_estimation` (`Optional[schama.abstract_recognition_response]`): 最新の感情・思考の推定結果。
- `history` (`List[Dict[str, Any]]]`): 推定とフィードバックの履歴。

#### 2.3. メソッド

##### `__init__(self, storage: RAGStorage, lm_client: Optional[LMStudioClient] = None)`
- **説明:** `ConcreteUnderstanding`のインスタンスを初期化します。
- **引数:**
    - `storage`: `RAGStorage`のインスタンス。
    - `lm_client` (任意): `LMStudioClient`のインスタンス。指定されない場合は新しいインスタンスが作成されます。

##### `start_inference(self, field_info_input: str) -> Optional[schama.abstract_recognition_response]`
- **説明:** 推論プロセスのエントリーポイントです。初期状況を受け取り、一連の処理（RAGクエリ作成、経験検索、初期推定）を実行します。
- **引数:**
    - `field_info_input`: ユーザーから入力された初期の状況説明。
- **戻り値:** 初期の推定結果 (`abstract_recognition_response`オブジェクト)。失敗した場合は`None`。

##### `process_user_feedback(self, user_input: str) -> Optional[schama.abstract_recognition_response]`
- **説明:** ユーザーからのフィードバックを処理し、状況を再評価して推定を更新します。
- **引数:**
    - `user_input`: ユーザーからのフィードバック文字列。
- **戻り値:** 更新された推定結果 (`abstract_recognition_response`オブジェクト)。失敗した場合は`None`。

##### `_create_rag_query(self, field_info_input: str) -> str`
- **説明:** (内部メソッド) 状況説明文から、RAG検索に適した高品質な検索クエリをLLMを用いて生成します。
- **引数:**
    - `field_info_input`: ユーザーから入力された初期の状況説明。
- **戻り値:** 生成された検索クエリ文字列。

##### `_evaluate_retrieved_experiences(self, experiences: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]`
- **説明:** (内部メソッド) RAGによって検索された経験の関連性を評価します。現在はプレースホルダーであり、取得した経験をそのまま返します。
- **引数:**
    - `experiences`: 検索された経験のリスト。
    - `query`: 検索に使用されたクエリ。
- **戻り値:** 評価後の経験のリスト。

##### `_run_estimation(self, feedback: Optional[str] = None)`
- **説明:** (内部メソッド) LLMを使用して実際の推定処理を実行します。経験、状況、および（もしあれば）フィードバックをコンテキストとして、感情と思考を予測します。
- **引数:**
    - `feedback` (任意): ユーザーからのフィードバック文字列。

## 3. スタンドアロン関数

### `architecture_base(storage: RAGStorage, field_info_input: str) -> Optional[schama.abstract_recognition_response]`

- **説明:** 後方互換性のために残されている関数です。`ConcreteUnderstanding`クラスの対話的な機能を使わず、一度の呼び出しで初期推定のみを実行します。
- **引数:**
    - `storage`: `RAGStorage`のインスタンス。
    - `field_info_input`: ユーザーから入力された初期の状況説明。
- **戻り値:** 初期の推定結果 (`abstract_recognition_response`オブジェクト)。失敗した場合は`None`。

## 4. 依存関係

- `lm_studio_rag.storage.RAGStorage`: 経験の永続化と検索。
- `lm_studio_rag.lm_studio_client.LMStudioClient`: LLMとの通信。
- `.schema_architecture`: 推定結果を格納するためのPydanticスキーマ。
- `pydantic`: データバリデーション。

## 5. 使用例

```python
from lm_studio_rag.storage import RAGStorage
from architecture.concrete_understanding.base import ConcreteUnderstanding

# 1. ストレージを初期化
storage = RAGStorage(db_path="path/to/your/rag.db")
# (事前にstorageに経験が保存されていると仮定)

# 2. ConcreteUnderstandingのインスタンスを作成
understanding_process = ConcreteUnderstanding(storage)

# 3. 初期状況を与えて推論を開始
situation = "今日の会議で、上司から厳しいフィードバックを受けた。"
initial_estimation = understanding_process.start_inference(situation)

if initial_estimation:
    print(f"初期推定（感情）: {initial_estimation.emotion_estimation}")
    print(f"初期推定（思考）: {initial_estimation.think_estimation}")

# 4. ユーザーからのフィードバックを処理
feedback = "いや、そこまで落ち込んではいない。むしろ、どう改善しようかと考えている。"
updated_estimation = understanding_process.process_user_feedback(feedback)

if updated_estimation:
    print(f"更新後の推定（感情）: {updated_estimation.emotion_estimation}")
    print(f"更新後の推定（思考）: {updated_estimation.think_estimation}")
```
