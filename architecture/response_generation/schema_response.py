from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from ..abstract_recognition.schama_architecture import abstract_recognition_response
from ..concrete_understanding.schema_architecture import EpisodeData # Assuming we might want to reference this


# init
# abstract_understanding_defalt = abstract_recognition_response()
# abstract_understanding_defalt.emotion_estimation = "悲しい"
# abstract_understanding_defalt.think_estimation = "この人は楽しい、でも私は過去に同じような状況で笑うしかなかった。楽しいのかな。"
class UserResponse(BaseModel):
    """
    ユーザーへの最終的な応答を生成するための統合された推論結果を保持するスキーマ。
    抽象的理解、具体的理解、そしてそれらに基づく意思決定と行動推論を含む。
    """
    abstract_understanding: abstract_recognition_response = Field(None, description="抽象的理解の推論結果")
    concrete_understanding_summary: str = Field(None, description="具体的な状況理解の要約（時間、場所、人間環境などを含む）")
    inferred_decision: str = Field(None, description="具体的理解に基づいてAIが行うと推論される意思決定")
    inferred_action: str = Field(None, description="意思決定に基づいてAIが行うと推論される行動")
    generated_response_text: str = Field(None, description="ユーザーに提示される最終的な応答テキスト")