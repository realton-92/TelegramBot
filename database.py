import os
import aiosqlite

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_NAME = os.path.join(DB_DIR, 'void_runner.db')

async def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT,
                credits INTEGER DEFAULT 0,
                cpu_level INTEGER DEFAULT 1,
                proxy_level INTEGER DEFAULT 1,
                current_mission_id INTEGER DEFAULT 0
            )
        ''')
        
        # Добавляем колонки инвентаря, если их еще нет
        try:
            await db.execute('ALTER TABLE users ADD COLUMN emp_count INTEGER DEFAULT 0')
        except Exception:
            pass
            
        try:
            await db.execute('ALTER TABLE users ADD COLUMN freeze_count INTEGER DEFAULT 0')
        except Exception:
            pass
            
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "nickname": row[1],
                    "credits": row[2],
                    "cpu_level": row[3],
                    "proxy_level": row[4],
                    "current_mission_id": row[5],
                    "emp_count": row[6] if len(row) > 6 else 0,
                    "freeze_count": row[7] if len(row) > 7 else 0
                }
            return None

async def create_user(user_id: int, nickname: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, nickname) VALUES (?, ?)', (user_id, nickname))
        await db.commit()

async def update_user_credits(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def update_user_mission(user_id: int, mission_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET current_mission_id = ? WHERE user_id = ?', (mission_id, user_id))
        await db.commit()

async def update_user_stat(user_id: int, stat_name: str, new_value: int):
    """Универсальная функция для обновления CPU, Proxy или инвентаря"""
    allowed_stats = ['cpu_level', 'proxy_level', 'emp_count', 'freeze_count']
    if stat_name not in allowed_stats:
        return
        
    async with aiosqlite.connect(DB_NAME) as db:
        query = f'UPDATE users SET {stat_name} = ? WHERE user_id = ?'
        await db.execute(query, (new_value, user_id))
        await db.commit()
