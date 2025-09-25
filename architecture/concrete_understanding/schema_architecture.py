# architecture/concrete_understanding/schema_architecture.py

"""
このファイルは、アーキテクチャの「具象的理解（concrete_understanding）」部分のPydanticモデルを定義します。
プロジェクトドキュメントで定義されている「エピソードデータ（Episode Data）」フォーマットに基づいています。
これらのモデルは、システム全体でエピソードデータを型安全に取り扱うことを保証します。
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EmotionAnalysis(BaseModel):
    """AIによる感情分析結果"""
    primary_emotion: Optional[str] = Field(None, description="最も顕著な感情")
    secondary_emotions: Optional[List[str]] = Field(None, description="その他に検出された感情")
    sentiment_polarity: Optional[str] = Field(None, description="全体的な感情の極性 (positive, negative, neutral, mixed)")
    sentiment_intensity: Optional[float] = Field(None, ge=0.0, le=1.0, description="感情の強度")
    emotion_keywords: Optional[List[str]] = Field(None, description="感情判断の根拠となったキーワード")

class NamedEntity(BaseModel):
    """抽出された固有表現"""
    text: str = Field(None, description="固有表現のテキスト")
    type: str = Field(None, description="固有表現の種類 (PERSON, LOCATION, etc.)")

class Summarization(BaseModel):
    """AIによるエピソードの要約"""
    short_summary: str = Field(None, description="短い要約文")
    key_points: List[str] = Field(["...cute"], description="主要なポイントのリスト")

class DevelopmentalStageEstimation(BaseModel):
    """AIが正規化した出来事の時期と推定発達段階"""
    start_age: Optional[int] = None
    end_age: Optional[int] = None
    developmental_stage_estimation: Optional[str] = None

class SensesInvolvedSummary(BaseModel):
    """その時の五感の記憶の要約"""
    visual: Optional[str] = None
    auditory: Optional[str] = None
    olfactory: Optional[str] = None
    tactile: Optional[str] = None
    gustatory: Optional[str] = None

class TraumaEventDetails(BaseModel):
    """トラウマ・イベントに関する詳細情報"""
    user_reported_event_timing_text: Optional[str] = Field(None, description="ユーザーが語った出来事の時期")
    estimated_event_period: Optional[DevelopmentalStageEstimation] = Field(None, description="AIが正規化した出来事の時期と推定発達段階")
    senses_involved_summary: Optional[SensesInvolvedSummary] = Field(None, description="その時の五感の記憶の要約")
    immediate_emotions_felt_summary: Optional[List[str]] = Field(None, description="その場で感じた主要な一次感情のリスト")
    immediate_thoughts_summary: Optional[List[str]] = Field(None, description="その場で頭に浮かんだ思考の主要なもののリスト")
    physical_reactions_summary: Optional[List[str]] = Field(None, description="その時の身体反応の主要なもののリスト")
    perceived_threat_level_description: Optional[str] = Field(None, description="感じた脅威の度合いに関する記述")

class LinkedToPersonDataEntry(BaseModel):
    """Person Dataとの連携情報"""
    target_person_data_key: str = Field(None, description="Person Data内のトップレベルのキー名")
    target_entry_id: str = Field(None, description="そのキー内の具体的なエントリのID")
    relationship_type: str = Field(None, description="関係性の種類 (is_evidence_for, etc.)")

class RelatedEpisode(BaseModel):
    """他のエピソードとの連携情報"""
    episode_id: str = Field(None, description="関連する他のエピソードのID")
    relationship_type: str = Field(None, description="関係性の種類 (is_response_to, etc.)")

class EpisodeData(BaseModel):
    """
    ユーザーとの具体的な対話や出来事の記録（エピソード）を保持するデータモデル。
    YourselfLMの記憶の最小単位となる。
    """
    episode_id: str = Field(None, description="エピソードの一意な識別子 (UUIDなど)")
    thread_id: str = Field(None, description="このエピソードが属する対話スレッドのID")
    timestamp: datetime = Field(None, description="このエピソードが記録された正確な日時 (ISO 8601形式)")
    sequence_in_thread: int = Field(0, description="スレッド内での発言・記録順序")

    source_type: str = Field(None, description="このエピソードの源泉 (user_free_dialogue, etc.)")
    author: str = Field(None, description="発言者 (user, ai_persona_standard_analyst, etc.)")

    content_type: str = Field(None, description="エピソード内容の種別 (factual_statement, etc.)")
    text_content: str = Field(None, description="ユーザーの元発言、AIの応答、あるいはシステムメッセージのテキスト内容")

    # --- AIによる自動解析情報 ---
    language: Optional[str] = Field(None, description="テキストの言語コード (ja, en, etc.)")
    emotion_analysis: Optional[EmotionAnalysis] = Field(None, description="感情分析結果")
    keywords: Optional[List[str]] = Field(None, description="抽出された主要キーワード")
    topics: Optional[List[str]] = Field(None, description="推定されるトピック")
    named_entities: Optional[List[NamedEntity]] = Field(None, description="抽出された固有表現")
    summarization: Optional[Summarization] = Field(None, description="AIによるこのエピソードの短い要約")

    # --- トラウマ・イベント関連情報 ---
    is_trauma_event: bool = Field(False, description="このエピソードがトラウマ・イベントそのものを記述しているか")
    trauma_event_details: Optional[TraumaEventDetails] = Field(None, description="トラウマ・イベントの詳細情報")

    # --- ユーザーによる評価・状態管理 ---
    user_importance_rating: Optional[str] = Field(None, description="ユーザーによるこのエピソードの重要度評価 (very_high, high, etc.)")
    user_labels_or_tags: Optional[List[str]] = Field(None, description="ユーザーが付与した自由なラベルやタグ")
    status: str = Field(None, description="エピソードの状態 (active, archived_by_user, etc.)")
    sensitivity_level: str = Field(None, description="このエピソードの機微度 (low, medium, high, etc.)")

    # --- データ連携 ---
    linked_to_person_data_entries: Optional[List[LinkedToPersonDataEntry]] = Field(None, description="このエピソードが影響を与えた、または根拠となるPerson Data内のエントリIDリスト")
    related_episode_ids: Optional[List[RelatedEpisode]] = Field(None, description="このエピソードが直接的に関連する他のエピソードID")

    # --- メタデータ ---
    user_notes: Optional[str] = Field(None, description="ユーザーがこのエピソードに対して付加したメモ")
    last_accessed_by_ai_for_analysis: Optional[datetime] = Field(None, description="AIが最後にこのエピソードを主要な分析対象として参照した日時")
    last_reviewed_by_user: Optional[datetime] = Field(None, description="ユーザーが最後にこのエピソードを棚卸しでレビューした日時")
