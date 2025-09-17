from pydantic import BaseModel, EmailStr, Field,ConfigDict
from typing import List, Optional, Dict, Any
import datetime # Pydanticでdatetime型を扱うために必要

# ======== Architecture Schama ========
class abstract_recognition_response(BaseModel):
    emotion_estimation: str
    think_estimation: str
