# app/schemas.py
from pydantic import BaseModel, EmailStr, Field,ConfigDict
from typing import List, Optional, Dict, Any
import datetime # Pydanticでdatetime型を扱うために必要



# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    user_id: str  # ユーザーIDはユニークな識別子として使用
    password: str  # パスワードは作成時に平文で受け取り、サーバー側でハッシュ化する

class UserUpdate(BaseModel): # ユーザー情報更新用 (部分更新を想定)
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    # パスワード変更は別のエンドポイントや特別な処理を挟むことが多いので、ここでは含めない例

class User(UserBase): # APIレスポンス用 (DBモデルから変換)
    user_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    # password_hash は通常レスポンスに含めない

    model_config = ConfigDict(from_attributes=True) # Pydantic V2


# --- Message Schemas ---
class EditHistoryEntry(BaseModel):
    edited_at: datetime.datetime
    previous_content: str

class MessageBase(BaseModel):
    role: str
    context: str
    feeling: Optional[str] = None
    cache: Optional[Dict[str, Any]] = None

class MessageCreate(MessageBase):
    sender_user_id: Optional[str] = None # AIの場合は指定しない

class Message(MessageBase):
    message_id: int
    thread_id: str
    sender_user_id: Optional[str] = None
    edit_history: Optional[List[EditHistoryEntry]] = None
    timestamp: datetime.datetime

    # Pydantic V1
    class Config:
        # orm_mode = True
        # Pydantic V2
        model_config = ConfigDict(from_attributes=True)

class MessageCreate(MessageBase):
    sender_user_id: Optional[str] = None
    answered_question_id: Optional[int] = None # ★追加


# --- Thread Schemas ---
class ThreadBase(BaseModel):
    mode: str
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None

class ThreadCreate(ThreadBase):
    # スレッド作成時に最初のメッセージも受け取るならここに定義
    # initial_message_context: Optional[str] = None
    pass


class Thread(ThreadBase):
    id: str
    owner_user_id: str
    timestamp: datetime.datetime
    messages: List[Message] = [] # スレッド取得時にメッセージも返す場合

    # Pydantic V1
    class Config:
        # orm_mode = True
        # Pydantic V2
        model_config = ConfigDict(from_attributes=True)


# --- Feedback Schemas ---
class FeedbackBase(BaseModel):
    correct: int = Field(..., ge=-2, le=2) # ge, le で数値範囲バリデーション
    user_comment: Optional[str] = None

class FeedbackCreate(FeedbackBase):
    message_id: int
    # user_idは認証情報から取得するため、リクエストボディには含めないのが一般的

class Feedback(FeedbackBase):
    feedback_id: int
    message_id: int
    user_id: str
    timestamp: datetime.datetime

    class Config:
        model_config = ConfigDict(from_attributes=True)


# --- Question Schemas ---

class QuestionBase(BaseModel): # Question作成・更新のベース
    question_text: str
    reason_for_question: Optional[str] = None
    thread_id: Optional[str] = None
    priority: int = 0
    status: str = 'pending' # これは、'pending', 'asked', 'answered' などのステータスを持つと仮定　基本的に質問を作成した際に初期値は 'pending'とする
    source: Optional[str] = None
    related_message_id: Optional[int] = None

class QuestionCreate(QuestionBase): # POSTリクエストボディ用
    pass # QuestionBase を継承し、user_id はパスパラメータで取るのでここには不要


class QuestionUpdate(BaseModel): # PUTリクエストボディ用 (部分更新)
    question_text: Optional[str] = None
    reason_for_question: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None

class NextQuestionResponse(BaseModel):
    question_id: Optional[int] = None
    question_text: Optional[str] = None
    guidance: Optional[str] = None # AIが生成した回答ガイダンス
    status: Optional[str] = None # 'asked' や 'no_pending_questions' など


class Question(QuestionBase): # GETレスポンス用 (DBモデルから変換)
    question_id: int
    user_id: str
    created_at: datetime.datetime
    asked_at: Optional[datetime.datetime] = None
    answered_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)

# --- Qeustion_links ---
class QuestionLink_main(BaseModel):
    question_id: int
    user_id: str

class QuestionLink_sub(QuestionLink_main):
    sub_question_id: int
    
    


# --- Auth Schemas ---
class GoogleToken(BaseModel):
    token: str

class AuthResponse(BaseModel):
    message: str
    user_id: str
    email: str
    name: Optional[str] = None
    is_new_user: bool
