
import asyncio
import os
from logging import getLogger

from .db_database import async_engine, Base, AsyncSessionLocal
from . import crud, schemas, models

logger = getLogger(__name__)

# db_database.pyで定義されているデータベースファイル名に合わせる
DATABASE_FILE = "test.db"

async def initialize_database():
    """
    データベースファイルが存在しない場合に、スキーマを初期化し、
    テスト用の初期データを投入する。
    """
    if os.path.exists(DATABASE_FILE):
        # データベースが既に存在する場合は何もしない
        return

    logger.info(f"データベース '{DATABASE_FILE}' が見つかりません。新しいデータベースを作成し、初期化します。")

    # 1. テーブルをすべて作成する
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("テーブルが正常に作成されました。")

    # 2. 初期データを投入する
    async with AsyncSessionLocal() as db:
        try:
            # --- テストユーザーの作成 ---
            logger.info("テストユーザーを作成します...")
            # api_use_db.pyのモックに合わせてuser_idを"1"に設定
            test_user_id = "1"
            
            existing_user = await crud.get_user(db, user_id=test_user_id)
            if not existing_user:
                # crud.create_userがidをセットしないため、ここで直接モデルを作成・追加する
                hashed_password = "password" + "_hashed"  # crud.py内の仮ハッシュ化ロジック
                user = models.User(
                    id=test_user_id,
                    email="test@example.com",
                    name="Test User",
                    password_hash=hashed_password
                )
                db.add(user)
                await db.commit()  # ユーザーをまず永続化
                await db.refresh(user)
                
                logger.info(f"ユーザー '{user.name}' (ID: {user.id}) が作成されました。")

                # --- 初期スレッドとメッセージの作成 ---
                logger.info(f"ユーザー '{user.name}' のための初期スレッドを作成します...")
                thread_data = schemas.ThreadCreate(mode="chat", title="最初のスレッド")
                thread = await crud.create_thread(db=db, thread_data=thread_data, owner_user_id=user.id)
                logger.info(f"スレッド '{thread.title}' (ID: {thread.id}) が作成されました。")

                message_data_1 = schemas.MessageCreate(
                    role="user", context="こんにちは！これは最初のメッセージです。", sender_user_id=user.id
                )
                await crud.create_message(db=db, message_data=message_data_1, thread_id=thread.id)

                message_data_2 = schemas.MessageCreate(
                    role="assistant", context="こんにちは、Test Userさん。何かお手伝いできることはありますか？", sender_user_id=None
                )
                await crud.create_message(db=db, message_data=message_data_2, thread_id=thread.id)
                logger.info("初期メッセージが作成されました。")
                
                logger.info("初期データの投入が完了しました。")

            else:
                logger.info(f"ユーザー (ID: {test_user_id}) は既に存在していたため、作成をスキップしました。")

        except Exception as e:
            # crud関数が個別にcommitするため、完全なロールバックは難しい
            logger.error(f"データベースの初期化中にエラーが発生しました: {e}", exc_info=True)
            await db.rollback()
            raise

def run_db_initialization():
    """
    非同期の初期化処理を同期的に実行するためのラッパー関数。
    FastAPIなどの非同期フレームワークで利用されることを想定し、
    実行中のイベントループを妨害しないようにする。
    """
    try:
        # 既に実行中のイベントループがあれば、そのループでタスクとして実行
        loop = asyncio.get_running_loop()
        loop.create_task(initialize_database())
    except RuntimeError:
        # 実行中のイベントループがない場合（＝通常のPythonスクリプトとして実行された場合）
        # 新しいイベントループを作成して実行
        asyncio.run(initialize_database())

# モジュールがインポートされた際に初期化処理を実行
run_db_initialization()
