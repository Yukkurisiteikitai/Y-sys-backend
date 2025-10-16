from typing import Annotated
from fastapi import Depends
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from architecture.concrete_understanding.base import ConcreteUnderstanding
from architecture.user_response.generator import UserResponseGenerator

# これらは「プレースホルダー」
# 実体はmain_api.pyのapp.dependency_overridesで設定される

def get_storage() -> RAGStorage:
    """RAGStorageを返す（実体はmain.pyで注入）"""
    raise NotImplementedError("Must be overridden in main_api.py")

def get_lm_client() -> LMStudioClient:
    """LMStudioClientを返す（実体はmain.pyで注入）"""
    raise NotImplementedError("Must be overridden in main_api.py")

def get_concrete_process() -> ConcreteUnderstanding:
    """ConcreteUnderstandingを返す（実体はmain.pyで注入）"""
    raise NotImplementedError("Must be overridden in main_api.py")

def get_response_gen() -> UserResponseGenerator:
    """UserResponseGeneratorを返す（実体はmain.pyで注入）"""
    raise NotImplementedError("Must be overridden in main_api.py")
