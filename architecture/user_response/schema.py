# architecture/user_response/schema.py
from pydantic import BaseModel, Field
from typing import Optional, Dict

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
    thought_process: Dict[str, str] = Field(
        default={},
        description="応答生成に至る思考プロセス（感情的トリガー、情報的インプット、思考の変遷）"
    )
    nuance: str = Field(
        default="",
        description="応答の際の、観察可能な非言語的な態度や雰囲気。"
    )
    dialogue: str = Field(
        default="",
        description="ユーザーへの実際のセリフ。"
    )
    behavior: str = Field(
        default="",
        description="セリフに伴う、客観的に観測可能な物理的行動。"
    )
