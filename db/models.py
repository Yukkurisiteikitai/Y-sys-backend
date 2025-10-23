# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func

import datetime

from .db_database import Base

class User(Base):
    __tablename__ = "User"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    threads = relationship("Thread", back_populates="owner", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    questions_for_this_user = relationship("Question", back_populates="target_user", foreign_keys="[Question.user_id]", cascade="all, delete-orphan")
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="[Message.sender_user_id]", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="user", cascade="all, delete-orphan")
    person_data_entries = relationship("PersonDataEntry", back_populates="user", cascade="all, delete-orphan")
    user_question_progress = relationship("UserQuestionProgress", back_populates="user", cascade="all, delete-orphan")
    qa_sessions = relationship("QASession", back_populates="user")

class Thread(Base):
    __tablename__ = "Thread"

    id = Column(String, primary_key=True, nullable=False, index=True)
    owner_user_id = Column(String, ForeignKey("User.id"), nullable=False, index=True)
    mode = Column(String, nullable=False)
    title = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    related_questions = relationship("Question", back_populates="thread", foreign_keys="[Question.thread_id]", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="thread", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint(mode.in_(['chat', 'search']), name='thread_mode_check'),)

class Message(Base):
    __tablename__ = "Message"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    thread_id = Column(String, ForeignKey("Thread.id"), nullable=False, index=True)
    sender_user_id = Column(String, ForeignKey("User.id"), nullable=True, index=True)
    role = Column(String, nullable=False)
    context = Column(Text, nullable=False)
    feeling = Column(String, nullable=True)
    cache = Column(JSON, nullable=True)
    edit_history = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("Thread", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_user_id])
    feedbacks = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")
    follow_up_questions = relationship("Question", back_populates="originating_message", foreign_keys="[Question.related_message_id]", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint(role.in_(['system', 'user', 'assistant', 'ai_question']), name='message_role_check'),)

class Feedback(Base):
    __tablename__ = "Feedback"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    message_id = Column(Integer, ForeignKey("Message.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("User.id"), nullable=False, index=True)
    correct = Column(Integer, nullable=False)
    user_comment = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")

    __table_args__ = (CheckConstraint(correct >= -2, name='feedback_correct_min_check'), CheckConstraint(correct <= 2, name='feedback_correct_max_check'),)

class Question(Base):
    __tablename__ = "Question"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(String, ForeignKey("User.id"), nullable=False, index=True)
    thread_id  = Column(String, ForeignKey("Thread.id"), nullable=True, index=True)
    question_text  = Column(String, nullable=False)
    reason_for_question  = Column(String, nullable=True)
    priority  = Column(Integer, default=0, nullable=False)
    status  = Column(String, nullable=False, default='pending')
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    asked_at  = Column(DateTime(timezone=True), nullable=True)
    answered_at  = Column(DateTime(timezone=True), nullable=True)
    related_message_id  = Column(Integer, ForeignKey("Message.id"), nullable=True, index=True)
    source  = Column(Text, nullable=True)

    target_user = relationship("User", back_populates="questions_for_this_user", foreign_keys=[user_id])
    thread = relationship("Thread", back_populates="related_questions", foreign_keys=[thread_id])
    originating_message = relationship("Message", back_populates="follow_up_questions", foreign_keys=[related_message_id])

    __table_args__ = (CheckConstraint(status.in_(['pending', 'asked', 'answered', 'skipped']), name='question_status_check'),)

class QuestionLink(Base):
    __tablename__ = "QuestionLink"
    question_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="0", nullable=False)
    sub_question_id = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class QASession(Base):
    __tablename__ = "qa_sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("User.id"), nullable=False, index=True)
    target_tag_name = Column(String, nullable=False, index=True)
    session_type = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)
    
    total_questions = Column(Integer, default=0, nullable=False)
    completed_questions = Column(Integer, default=0, nullable=False)
    average_resolution_score = Column(Float, nullable=True)
    total_follow_ups = Column(Integer, default=0, nullable=False)
    
    episode_generated = Column(Boolean, default=False)
    
    started_at = Column(DateTime(timezone=True), default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), default=func.now())
    
    session_metadata = Column(JSON, nullable=True)
    
    user = relationship("User", back_populates="qa_sessions")
    generated_episodes = relationship("Episode", back_populates="qa_session", foreign_keys="[Episode.qa_session_id]")
    progresses = relationship("UserQuestionProgress", back_populates="qa_session")
    
    __table_args__ = (
        CheckConstraint(session_type.in_(['initialization', 'deep_dive', 'clarification']), name='qa_session_type_check'),
        CheckConstraint(status.in_(['active', 'completed', 'abandoned']), name='qa_session_status_check'),
    )

class Episode(Base):
    __tablename__ = "episodes"

    id = Column(String, primary_key=True, index=True)
    thread_id = Column(String, ForeignKey("Thread.id"), nullable=False)
    user_id = Column(String, ForeignKey("User.id"), nullable=False)
    timestamp = Column(DateTime, default=func.now())
    sequence_in_thread = Column(Integer, nullable=False)
    source_type = Column(String, nullable=False)
    author = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    text_content = Column(Text, nullable=False)
    language = Column(String, default="ja", nullable=False)
    emotion_analysis = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    topics = Column(JSON, nullable=True)
    named_entities = Column(JSON, nullable=True)
    summarization = Column(JSON, nullable=True)
    is_trauma_event = Column(Boolean, default=False)
    trauma_event_details = Column(JSON, nullable=True)
    user_importance_rating = Column(String, default="not_set", nullable=True)
    user_labels_or_tags = Column(JSON, nullable=True)
    status = Column(String, default="active", nullable=False)
    sensitivity_level = Column(String, default="medium", nullable=False)
    user_notes = Column(Text)
    last_accessed_by_ai_for_analysis = Column(DateTime)
    last_reviewed_by_user = Column(DateTime)
    vector_id = Column(String, unique=True, index=True, nullable=True)
    vector_synced_at = Column(DateTime, nullable=True)
    vector_sync_status = Column(String, default="pending", nullable=False)
    embedding_model_version = Column(String, nullable=True)
    processed_text_for_embedding = Column(Text, nullable=True)
    is_from_qa_session = Column(Boolean, default=False)
    qa_session_id = Column(String, ForeignKey("qa_sessions.id"), nullable=True, index=True)
    
    thread = relationship("Thread", back_populates="episodes")
    user = relationship("User", back_populates="episodes")
    person_data_entries = relationship("PersonDataEntry", secondary="person_data_episode_link", back_populates="linked_episodes")
    qa_session = relationship("QASession", back_populates="generated_episodes", foreign_keys=[qa_session_id])
    
    __table_args__ = (
        CheckConstraint(vector_sync_status.in_(['pending', 'synced', 'failed']), name='episode_vector_sync_status_check'),
        CheckConstraint(status.in_(['active', 'archived', 'deleted']), name='episode_status_check'),
        CheckConstraint(source_type.in_(['conversation', 'question_answer', 'import', 'system_generated']), name='episode_source_type_check'),
    )

class PersonDataEpisodeLink(Base):
    __tablename__ = 'person_data_episode_link'
    
    person_data_entry_id = Column(String, ForeignKey('person_data_entries.id'), primary_key=True)
    episode_id = Column(String, ForeignKey('episodes.id'), primary_key=True)
    contribution_weight = Column(Float, default=1.0, nullable=False)
    link_created_at = Column(DateTime, default=func.now())
    link_method = Column(String, nullable=False, default="ai_analysis")
    link_confidence = Column(Float, default=0.8, nullable=False)
    ai_reasoning = Column(Text, nullable=True)
    user_verified = Column(Boolean, default=False)
    user_verification_date = Column(DateTime, nullable=True)
    user_verification_comment = Column(Text, nullable=True)
    
    __table_args__ = (
        CheckConstraint(contribution_weight >= 0.0, name='link_contribution_weight_min_check'),
        CheckConstraint(contribution_weight <= 1.0, name='link_contribution_weight_max_check'),
        CheckConstraint(link_confidence >= 0.0, name='link_confidence_min_check'),
        CheckConstraint(link_confidence <= 1.0, name='link_confidence_max_check'),
        CheckConstraint(link_method.in_(['ai_analysis', 'user_manual', 'rule_based']), name='link_method_check'),
    )

class PersonDataEntry(Base):
    __tablename__ = "person_data_entries"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("User.id"), nullable=False)
    tag_name = Column(String, nullable=False, index=True)
    entry_date = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    source = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)
    sensitivity_level = Column(String, default="medium", nullable=False)
    user_notes = Column(Text)
    entry_content = Column(JSON, nullable=False)
    vector_id = Column(String, unique=True, index=True, nullable=True)
    vector_synced_at = Column(DateTime, nullable=True)
    vector_sync_status = Column(String, default="pending", nullable=False)
    embedding_model_version = Column(String, nullable=True)
    confidence_score = Column(Float, default=0.5, nullable=False)
    generation_method = Column(String, nullable=False, default="ai_inferred")
    ai_model_version = Column(String, nullable=True)
    analysis_timestamp = Column(DateTime, default=func.now())
    user_approval_status = Column(String, default="pending", nullable=False)
    user_approval_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    modification_history = Column(JSON, nullable=True)
    formatted_for_prompt = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="person_data_entries")
    linked_episodes = relationship("Episode", secondary="person_data_episode_link", back_populates="person_data_entries")
    
    __table_args__ = (
        CheckConstraint(confidence_score >= 0.0, name='person_data_confidence_min_check'),
        CheckConstraint(confidence_score <= 1.0, name='person_data_confidence_max_check'),
        CheckConstraint(user_approval_status.in_(['pending', 'approved', 'rejected', 'modified']), name='person_data_approval_status_check'),
        CheckConstraint(generation_method.in_(['ai_inferred', 'user_direct', 'hybrid']), name='person_data_generation_method_check'),
        CheckConstraint(status.in_(['active', 'archived', 'rejected']), name='person_data_status_check'),
    )

class InitializationQuestion(Base):
    __tablename__ = "initialization_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_progress = relationship("UserQuestionProgress", back_populates="init_question")

class UserQuestionProgress(Base):
    __tablename__ = "user_question_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("User.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("initialization_questions.id"), nullable=True, index=True)
    regular_question_id = Column(Integer, ForeignKey("Question.id"), nullable=True, index=True)
    answer_text = Column(Text, nullable=True)
    ai_evaluation = Column(JSON, nullable=True)
    attempt_count = Column(Integer, default=0)
    status = Column(String, default="pending", nullable=False)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolution_score = Column(Float, nullable=True)
    information_completeness = Column(Float, nullable=True)
    needs_follow_up = Column(Boolean, default=False)
    follow_up_topics = Column(JSON, nullable=True)
    parent_progress_id = Column(Integer, ForeignKey("user_question_progress.id"), nullable=True, index=True)
    follow_up_depth = Column(Integer, default=0)
    episode_conversion_status = Column(String, default="pending", nullable=False)
    generated_episode_id = Column(String, ForeignKey("episodes.id"), nullable=True, index=True)
    conversion_error_message = Column(Text, nullable=True)
    qa_session_id = Column(String, ForeignKey("qa_sessions.id"), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="user_question_progress")
    init_question = relationship("InitializationQuestion", back_populates="user_progress")
    regular_question = relationship("Question")
    parent_progress = relationship("UserQuestionProgress", remote_side=[id], backref="follow_up_progresses", foreign_keys=[parent_progress_id])
    generated_episode = relationship("Episode", foreign_keys=[generated_episode_id])
    qa_session = relationship("QASession", back_populates="progresses")
    
    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'answered', 'passed', 'failed', 'converted']), name='progress_status_check'),
        CheckConstraint(episode_conversion_status.in_(['pending', 'in_progress', 'completed', 'failed']), name='progress_episode_conversion_status_check'),
        CheckConstraint(resolution_score.between(0.0, 1.0) | resolution_score.is_(None), name='progress_resolution_score_range_check'),
    )

class AIEvaluationLog(Base):
    __tablename__ = "ai_evaluation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_progress_id = Column(Integer, ForeignKey("user_question_progress.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    ai_response = Column(JSON, nullable=False)
    evaluation_score = Column(Integer, nullable=False)
    is_passed = Column(Boolean, nullable=False)
    feedback_text = Column(Text, nullable=True)
    follow_up_question = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())