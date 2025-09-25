# architecture/user_response/schema.py
from pydantic import BaseModel, Field
from typing import Optional

class UserResponse(BaseModel):
    """
    抽象的理解と具象的理解を統合し、推論された最終的な応答の構造を定義します。
    """
    inferred_decision: str = Field(
        default="",
        description="AIによるデフォルメ（抽象化）と具現化（具体化）のプロセスを経て推論された、ユーザーが下す可能性のある意思決定。"
    )
    inferred_action: str = Field(
        default="",
        description="推論された意思決定に基づき、ユーザーが取る可能性のある具体的な行動。"
    )
    final_response: str = Field(
        default="",
        description="上記の推論を踏まえ、ユーザーの状況や感情に寄り添った、最終的な応答メッセージ。"
    )
