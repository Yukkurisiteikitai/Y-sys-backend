from fastapi import FastAPI
from pydantic_settings import BaseSettings

# ========================================
# 設定クラス
# ========================================
class Settings(BaseSettings):
    # データベース
    USE_MEMORY_STORAGE: bool = True
    VECTOR_DB_PATH: str = "./chroma_db"
    
    # LM Studio
    LM_STUDIO_BASE_URL: str = "http://localhost:1234/v1"
    LM_STUDIO_MODEL: str = "gemma-3-1b-it"
    
    # API
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # 環境
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"

settings = Settings()

# ========================================
# 依存関係の構築（ここで全て束ねる）
# ========================================
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from architecture.concrete_understanding.base import ConcreteUnderstanding
from architecture.user_response.generator import UserResponseGenerator

storage = RAGStorage(USE_MEMORY_RUN=settings.USE_MEMORY_STORAGE)
lm_client = LMStudioClient(base_url=settings.LM_STUDIO_BASE_URL)
concrete_process = ConcreteUnderstanding(storage=storage, lm_client=lm_client)
response_gen = UserResponseGenerator(lm_client=lm_client)

# ========================================
# FastAPIアプリケーション
# ========================================
app = FastAPI(
    title="YourselfLM API",
    version="1.0",
    description="ユーザーの思考プロセスをストリーミング形式で返却するAPI"
)

# CORS設定
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# 依存性注入の設定（実体を束ねる）
# ========================================
from dependencies import (
    get_storage, get_lm_client, 
    get_concrete_process, get_response_gen
)

app.dependency_overrides[get_storage] = lambda: storage
app.dependency_overrides[get_lm_client] = lambda: lm_client
app.dependency_overrides[get_concrete_process] = lambda: concrete_process
app.dependency_overrides[get_response_gen] = lambda: response_gen

# ========================================
# ルーター登録
# ========================================
from api.routers import sessions
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])

# ========================================
# 起動時処理
# ========================================
@app.on_event("startup")
async def startup_event():
    if settings.USE_MEMORY_STORAGE:
        import json
        from tqdm import tqdm
        print("テスト経験データをデータベースに追加")
        try:
            with open("sample_test_data.json")as f:
                data = json.load(f)
            for d in tqdm(data["sample_experience_data"], desc="Load-test-data",ncols=120, ascii="-="):
                storage.save_experience_data(text=d, metadata={"source": "initial"})
        except FileNotFoundError:
            print("sample_test_data.json not found, skipping data loading.")
    print(f"🚀 Application started in {settings.ENVIRONMENT} mode")

if __name__ == "__main__":
    import uvicorn
    from colorful_print import color_set_print
    print(f"Backend -> API-SERVER:{color_set_print('Boot ON','blue')} : http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
