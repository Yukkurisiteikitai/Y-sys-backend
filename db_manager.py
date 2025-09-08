# db_manager.py
import aiosqlite
import logging
import datetime
import os

DATABASE = 'bot_database.db'
logger = logging.getLogger('discord') # discord.pyのロガーを使う

async def initialize_database(db_path: str = DATABASE):
    """データベースを初期化し、必要なテーブルを作成する"""
    try:
        # データベースファイルのディレクトリが存在することを確認
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created database directory: {db_dir}")

        # データベースに接続（ファイルが存在しない場合は自動的に作成される）
        async with aiosqlite.connect(db_path) as db:
            # ユーザー設定などを保存するテーブル
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_info (
                    user_id INTEGER NOT NULL,
                    info_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    PRIMARY KEY (user_id, info_type)
                )
            ''')
            # LLMの会話履歴を保存するテーブル
            await db.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Episodesテーブルを作成
            await db.execute('''
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    text_content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    content_type TEXT,
                    emotion_analysis_json TEXT,
                    keywords_json TEXT,
                    topics_json TEXT,
                    named_entities_json TEXT,
                    summarization_json TEXT,
                    is_trauma_event BOOLEAN DEFAULT 0,
                    sensitivity_level TEXT,
                    user_importance_rating INTEGER,
                    user_labels_json TEXT,
                    user_notes TEXT,
                    collected_info_json TEXT,
                    completeness REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_info(user_id)
                )
            ''')
            # user_id と timestamp にインデックスを作成して検索を高速化
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_conv_history_user_id_timestamp
                ON conversation_history (user_id, timestamp)
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_episodes_user_id_timestamp
                ON episodes (user_id, timestamp)
            ''')
            await db.commit()
            logger.info(f"Database initialized with user_info, conversation_history, and episodes tables. (db_path={db_path})")
    except Exception as e:
        logger.error(f"Error initializing database at {db_path}: {e}")
        raise

# --- User Info Functions ---

async def add_user_info(user_id: int, info_type: str, content: str, db_path: str = DATABASE):
    """ユーザー情報を追加または更新する"""
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute('''
                INSERT INTO user_info (user_id, info_type, content)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, info_type) DO UPDATE SET content = excluded.content
            ''', (user_id, info_type, content))
            await db.commit()
            logger.info(f"Added/Updated info for user {user_id}: type='{info_type}'")
            return True
        except Exception as e:
            logger.error(f"Error adding/updating user info for {user_id}, type {info_type}: {e}")
            return False

async def get_user_info(user_id: int, db_path: str = DATABASE) -> dict:
    """特定のユーザーのすべての設定情報を取得する"""
    user_data = {}
    async with aiosqlite.connect(db_path) as db:
        try:
            async with db.execute('SELECT info_type, content FROM user_info WHERE user_id = ?', (user_id,)) as cursor:
                async for row in cursor:
                    user_data[row[0]] = row[1]
            logger.debug(f"Retrieved info for user {user_id}: {user_data}")
            return user_data
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return {} # エラー時は空辞書を返す

async def delete_user_info(user_id: int, db_path: str = DATABASE):
    """特定のユーザーのすべての設定情報を削除する"""
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute('DELETE FROM user_info WHERE user_id = ?', (user_id,))
            await db.commit()
            logger.info(f"Deleted all info for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user info for {user_id}: {e}")
            return False

async def get_specific_user_info(user_id: int, info_type: str, db_path: str = DATABASE) -> str | None:
    """特定のユーザーの特定のタイプの情報を取得する"""
    async with aiosqlite.connect(db_path) as db:
        try:
            async with db.execute('SELECT content FROM user_info WHERE user_id = ? AND info_type = ?', (user_id, info_type)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting specific info for user {user_id}, type {info_type}: {e}")
            return None

# --- Conversation History Functions ---

async def add_conversation_message(user_id: int, role: str, content: str, db_path: str = DATABASE):
    """会話履歴に新しいメッセージを追加する"""
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute('''
                INSERT INTO conversation_history (user_id, role, content)
                VALUES (?, ?, ?)
            ''', (user_id, role, content))
            await db.commit()
            logger.debug(f"Added conversation message for user {user_id}: role='{role}'")
            return True
        except Exception as e:
            logger.error(f"Error adding conversation message for user {user_id}: {e}")
            return False

async def get_conversation_history(user_id: int, limit: int | None = None, db_path: str = DATABASE) -> list[dict[str, str]]:
    """特定のユーザーの会話履歴を取得する (時系列順、オプションで件数制限)"""
    history = []
    query = '''
        SELECT role, content
        FROM conversation_history
        WHERE user_id = ?
        ORDER BY timestamp ASC
    '''
    params = (user_id,)

    if limit is not None and limit > 0:
        # 件数制限がある場合、最新のN件を取得するために逆順で取得し、後でPython側で反転させる
        # または、サブクエリやウィンドウ関数を使う方法もあるが、シンプルにするため取得後に反転する
        # -> やはりSQLで最新N件を取得するのが効率的なので、ORDER BY timestamp DESC LIMIT ? を使う
        query = '''
            SELECT role, content FROM (
                SELECT role, content, timestamp
                FROM conversation_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) ORDER BY timestamp ASC
        '''
        params = (user_id, limit)
        # logger.debug(f"Retrieving last {limit} messages for user {user_id}")
    # else:
        # logger.debug(f"Retrieving all messages for user {user_id}")


    async with aiosqlite.connect(db_path) as db:
        try:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    history.append({'role': row[0], 'content': row[1]})
            logger.debug(f"Retrieved {len(history)} conversation messages for user {user_id} (limit={limit})")
            return history
        except Exception as e:
            logger.error(f"Error getting conversation history for user {user_id}: {e}")
            return [] # エラー時は空リストを返す

async def delete_conversation_history(user_id: int, db_path: str = DATABASE):
    """特定のユーザーの会話履歴をすべて削除する"""
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute('DELETE FROM conversation_history WHERE user_id = ?', (user_id,))
            await db.commit()
            # 削除された行数を取得（オプション）
            changes = db.total_changes
            logger.info(f"Deleted conversation history for user {user_id}. Rows affected: {changes}")
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation history for user {user_id}: {e}")
            return False

# 注意: get_specific_user_history 関数は削除しました。
# 特定のメッセージが必要な場合は、get_conversation_history で全件取得するか、
# message_id で検索する関数を別途実装してください。

# --- Episodes Functions ---

async def add_episode(user_id: int, text_content: str, author: str, db_path: str = DATABASE, **kwargs):
    """エピソードを追加する"""
    async with aiosqlite.connect(db_path) as db:
        try:
            fields = ['user_id', 'text_content', 'author']
            values = [user_id, text_content, author]
            optional_fields = [
                'content_type', 'emotion_analysis_json', 'keywords_json',
                'topics_json', 'named_entities_json', 'summarization_json',
                'is_trauma_event', 'sensitivity_level', 'user_importance_rating',
                'user_labels_json', 'user_notes', 'collected_info_json', 'completeness'
            ]
            for field in optional_fields:
                if field in kwargs:
                    fields.append(field)
                    values.append(kwargs[field])
            placeholders = ', '.join(['?' for _ in fields])
            field_names = ', '.join(fields)
            query = f'''
                INSERT INTO episodes ({field_names})
                VALUES ({placeholders})
            '''
            cursor = await db.execute(query, values)
            await db.commit()
            episode_id = cursor.lastrowid
            logger.info(f"Added episode for user {user_id} (episode_id={episode_id})")
            return episode_id
        except Exception as e:
            logger.error(f"Error adding episode for user {user_id}: {e}")
            return None

async def get_episodes(user_id: int, limit: int | None = None, db_path: str = DATABASE) -> list[dict]:
    """特定のユーザーのエピソードを取得する"""
    episodes = []
    query = '''
        SELECT *
        FROM episodes
        WHERE user_id = ?
        ORDER BY timestamp DESC
    '''
    params = (user_id,)
    
    if limit is not None and limit > 0:
        query += ' LIMIT ?'
        params = (user_id, limit)
    
    async with aiosqlite.connect(db_path) as db:
        try:
            async with db.execute(query, params) as cursor:
                columns = [description[0] for description in cursor.description]
                async for row in cursor:
                    episode = dict(zip(columns, row))
                    episodes.append(episode)
            return episodes
        except Exception as e:
            logger.error(f"Error getting episodes for user {user_id}: {e}")
            return []

async def update_episode(episode_id: int, db_path: str = DATABASE, **kwargs):
    """エピソードを更新する"""
    if not kwargs:
        return False
        
    async with aiosqlite.connect(db_path) as db:
        try:
            set_clause = ', '.join([f"{field} = ?" for field in kwargs.keys()])
            values = list(kwargs.values())
            values.append(episode_id)
            
            query = f'''
                UPDATE episodes
                SET {set_clause}
                WHERE episode_id = ?
            '''
            
            cursor = await db.execute(query, values)
            await db.commit()
            
            # 更新された行数を確認
            if cursor.rowcount == 0:
                logger.info(f"Episode {episode_id} not found")
                return False
                
            logger.info(f"Updated episode {episode_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating episode {episode_id}: {e}")
            return False

async def delete_episode(episode_id: int, db_path: str = DATABASE):
    """エピソードを削除する"""
    async with aiosqlite.connect(db_path) as db:
        try:
            cursor = await db.execute('DELETE FROM episodes WHERE episode_id = ?', (episode_id,))
            await db.commit()
            
            # 削除された行数を確認
            if cursor.rowcount == 0:
                logger.info(f"Episode {episode_id} not found")
                return False
                
            logger.info(f"Deleted episode {episode_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting episode {episode_id}: {e}")
            return False
