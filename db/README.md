### 概要

以下は、定義された各モデルクラスに対応するデータベーステーブルの一覧と、それぞれのカラム詳細です。

1.  **User**: ユーザー情報を管理するテーブル
2.  **Thread**: 対話スレッドを管理するテーブル
3.  **Message**: 各スレッド内のメッセージを格納するテーブル
4.  **Feedback**: メッセージに対するフィードバックを管理するテーブル
5.  **Question**: AIがユーザーに尋ねる質問を管理するテーブル
6.  **QuestionLink**: 質問間の関連性を管理するテーブル
7.  **Episode**: 対話から抽出された重要な出来事（エピソード）を格納するテーブル
8.  **PersonDataEntry**: ユーザーの個人的なデータ（タグ付けされた情報）を格納するテーブル
9.  **PersonDataEpisodeLink**: `PersonDataEntry` と `Episode` をつなぐ中間テーブル
10. **InitializationQuestion**: 初期化フローで使用される質問のマスタテーブル
11. **UserQuestionProgress**: ユーザーの質問への回答状況を管理するテーブル
12. **AIEvaluationLog**: ユーザーの回答に対するAIの評価ログを保存するテーブル

---

### 1. User テーブル (`User`)

ユーザーアカウントの基本情報を格納します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | String | **主キー(PK)**, ユーザーの一意なID |
| `name` | String | ユーザー名 (NULL許容) |
| `email` | String | **一意制約(Unique)**, メールアドレス (必須) |
| `password_hash` | String | ハッシュ化されたパスワード (必須) |
| `created_at` | DateTime | 作成日時 (デフォルト: 現在時刻) |
| `updated_at` | DateTime | 更新日時 (デフォルト: 現在時刻, 更新時に自動更新) |

### 2. Thread テーブル (`Thread`)

ユーザーとの対話セッション（スレッド）の情報を格納します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | String | **主キー(PK)**, スレッドの一意なID (必須) |
| `owner_user_id` | String | **外部キー(FK)** → `User.id` (必須) |
| `mode` | String | スレッドのモード (必須, `chat` または `search`) |
| `title` | String | スレッドのタイトル (NULL許容) |
| `tags` | JSON | タグ情報 |
| `meta_data` | JSON | メタデータ |
| `timestamp` | DateTime | 作成日時 (デフォルト: 現在時刻) |

### 3. Message テーブル (`Message`)

スレッド内の個々のメッセージ（ユーザーの発言、AIの応答など）を格納します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | Integer | **主キー(PK)**, 自動インクリメント |
| `thread_id` | String | **外部キー(FK)** → `Thread.id` (必須) |
| `sender_user_id` | String | **外部キー(FK)** → `User.id`, 送信者がユーザーの場合に設定 (NULL許容) |
| `role` | String | メッセージの役割 (必須, `system`, `user`, `assistant`, `ai_question` のいずれか) |
| `context` | Text | メッセージの本文 (必須) |
| `feeling` | String | 感情情報 (NULL許容) |
| `cache` | JSON | キャッシュデータ |
| `edit_history` | JSON | 編集履歴 |
| `timestamp` | DateTime | 作成日時 (デフォルト: 現在時刻) |

### 4. Feedback テーブル (`Feedback`)

AIのメッセージに対するユーザーからのフィードバックを格納します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | Integer | **主キー(PK)**, 自動インクリメント |
| `message_id` | Integer | **外部キー(FK)** → `Message.id` (必須) |
| `user_id` | String | **外部キー(FK)** → `User.id` (必須) |
| `correct` | Integer | 評価スコア (必須, -2から2の範囲) |
| `user_comment` | Text | ユーザーからのコメント (NULL許容) |
| `timestamp` | DateTime | 作成日時 (デフォルト: 現在時刻) |

### 5. Question テーブル (`Question`)

AIが生成し、ユーザーに尋ねる必要がある質問を管理します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | Integer | **主キー(PK)**, 自動インクリメント |
| `user_id` | String | **外部キー(FK)** → `User.id` (質問対象のユーザー, 必須) |
| `thread_id` | String | **外部キー(FK)** → `Thread.id` (関連スレッド, NULL許容) |
| `question_text` | String | 質問の本文 (必須) |
| `reason_for_question` | String | 質問する理由 (NULL許容) |
| `priority` | Integer | 優先度 (デフォルト: 0) |
| `status` | String | 状態 (必須, `pending`, `asked`, `answered`, `skipped` のいずれか, デフォルト: `pending`) |
| `created_at` | DateTime | 作成日時 (デフォルト: 現在時刻) |
| `asked_at` | DateTime | ユーザーに質問した日時 (NULL許容) |
| `answered_at` | DateTime | ユーザーが回答した日時 (NULL許容) |
| `related_message_id` | Integer | **外部キー(FK)** → `Message.id` (派生元のメッセージ, NULL許容) |
| `source` | Text | 質問の生成元情報 (NULL許容) |

### 6. QuestionLink テーブル (`QuestionLink`)

質問間の親子関係や関連性を定義します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `question_id` | Integer | **主キー(PK)**, 親となる質問のID |
| `user_id` | String | ユーザーID (必須, デフォルト: "0") |
| `sub_question_id` | Integer | サブ（子）となる質問のID (必須, デフォルト: 0) |
| `created_at` | DateTime | 作成日時 (デフォルト: 現在時刻) |
| `updated_at` | DateTime | 更新日時 (デフォルト: 現在時刻, 更新時に自動更新) |

### 7. Episode テーブル (`episodes`)

対話の中から抽出された、ユーザーに関する重要な出来事や情報を構造化して格納します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | String | **主キー(PK)**, エピソードの一意なID |
| `thread_id` | String | **外部キー(FK)** → `Thread.id` (必須) |
| `user_id` | String | **外部キー(FK)** → `User.id` (必須) |
| `timestamp` | DateTime | タイムスタンプ (デフォルト: 現在時刻) |
| `sequence_in_thread` | Integer | スレッド内でのシーケンス番号 (必須) |
| `source_type` | String | ソースのタイプ (必須) |
| `author` | String | 発話者 (必須) |
| `content_type` | String | コンテンツのタイプ (必須) |
| `text_content` | Text | テキスト内容 (必須) |
| `language` | String | 言語 (デフォルト: "ja") |
| `emotion_analysis` | JSON | 感情分析結果 |
| `keywords` | JSON | キーワード |
| `topics` | JSON | トピック |
| `named_entities` | JSON | 固有表現抽出の結果 |
| `summarization` | JSON | 要約情報 |
| `is_trauma_event` | Boolean | トラウマ関連イベントか否か (デフォルト: False) |
| `trauma_event_details` | JSON | トラウマ関連イベントの詳細 |
| `user_importance_rating` | String | ユーザーによる重要度評価 (デフォルト: "not_set") |
| `user_labels_or_tags` | JSON | ユーザーによるタグ |
| `status` | String | 状態 (デフォルト: "active") |
| `sensitivity_level` | String | 機微レベル (デフォルト: "medium") |
| `user_notes` | Text | ユーザーによるメモ |
| `last_accessed_by_ai_for_analysis`| DateTime | AIが最後に分析でアクセスした日時 |
| `last_reviewed_by_user` | DateTime | ユーザーが最後にレビューした日時 |

### 8. PersonDataEntry テーブル (`person_data_entries`)

ユーザーに関する特定のタグ（例：幼少期の重要な経験）に分類された情報を格納します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | String | **主キー(PK)**, エントリの一意なID |
| `user_id` | String | **外部キー(FK)** → `User.id` (必須) |
| `tag_name` | String | タグ名 (例: "significant_childhood_experiences", 必須) |
| `entry_date` | DateTime | エントリ作成日 (デフォルト: 現在時刻) |
| `last_updated` | DateTime | 最終更新日 (デフォルト: 現在時刻, 更新時に自動更新) |
| `source` | String | 情報源 (例: "user_direct_input", 必須) |
| `status` | String | 状態 (デフォルト: "active") |
| `sensitivity_level` | String | 機微レベル (デフォルト: "medium") |
| `user_notes` | Text | ユーザーによるメモ |
| `entry_content` | JSON | タグに応じた具体的な内容 (必須) |

### 9. PersonDataEpisodeLink テーブル (`person_data_episode_link`)

`PersonDataEntry` と `Episode` の多対多の関連を表現するための中間テーブルです。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `person_data_entry_id` | String | **複合主キー(PK)**, **外部キー(FK)** → `person_data_entries.id` |
| `episode_id` | String | **複合主キー(PK)**, **外部キー(FK)** → `episodes.id` |

### 10. InitializationQuestion テーブル (`initialization_questions`)

ユーザー登録後の初期化フローで使われる質問のマスタデータを格納します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | Integer | **主キー(PK)**, 自動インクリメント |
| `question_text` | Text | 質問の本文 (必須) |
| `order_index` | Integer | 表示順 (必須) |
| `is_active` | Boolean | 有効かどうか (デフォルト: True) |
| `created_at` | DateTime | 作成日時 (デフォルト: 現在時刻) |

### 11. UserQuestionProgress テーブル (`user_question_progress`)

初期化質問や通常質問に対するユーザーごとの回答状況を追跡します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | Integer | **主キー(PK)**, 自動インクリメント |
| `user_id` | String | **外部キー(FK)** → `User.id` (必須) |
| `question_id` | Integer | **外部キー(FK)** → `initialization_questions.id` (初期化質問の場合, NULL許容) |
| `regular_question_id` | Integer | **外部キー(FK)** → `Question.id` (通常質問の場合, NULL許容) |
| `answer_text` | Text | ユーザーの回答内容 (NULL許容) |
| `ai_evaluation` | JSON | AIによる評価結果 |
| `attempt_count` | Integer | 回答試行回数 (デフォルト: 0) |
| `status` | String | 状態 (必須, `pending`, `answered`, `passed`, `failed` のいずれか, デフォルト: `pending`) |
| `answered_at` | DateTime | 回答日時 (NULL許容) |
| `created_at` | DateTime | 作成日時 (デフォルト: 現在時刻) |

### 12. AIEvaluationLog テーブル (`ai_evaluation_logs`)

`UserQuestionProgress` におけるAIの評価プロセスを詳細に記録します。

| カラム名 | データ型 | 制約 / 説明 |
| :--- | :--- | :--- |
| `id` | Integer | **主キー(PK)**, 自動インクリメント |
| `user_progress_id` | Integer | **外部キー(FK)** → `user_question_progress.id` (必須) |
| `question_text` | Text | 評価対象の質問テキスト (必須) |
| `answer_text` | Text | 評価対象の回答テキスト (必須) |
| `ai_response` | JSON | AIからの生のレスポンス (必須) |
| `evaluation_score` | Integer | 評価スコア (0-100, 必須) |
| `is_passed` | Boolean | 合格/不合格 (必須) |
| `feedback_text` | Text | AIからのフィードバック (NULL許容) |
| `follow_up_question`| Text | AIからの追加質問 (NULL許容) |
| `processing_time_ms` | Integer | 処理時間(ミリ秒) (NULL許容) |
| `model_version` | String | 使用したAIモデルのバージョン (NULL許容) |
| `created_at` | DateTime | 作成日時 (デフォルト: 現在時刻) |