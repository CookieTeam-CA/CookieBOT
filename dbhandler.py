import ezcord


class UserDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("data/database.db")

    async def setup(self):
        """Creates Database Tables."""
        await self.exec("""
        CREATE TABLE IF NOT EXISTS memes (
        user_id INTEGER DEFAULT NULL,
        msg_id INTEGER PRIMARY KEY,
        meme_url STRING DEFAULT NULL,
        meme_txt STRING DEFAULT NULL,
        votes INTEGER DEFAULT 0)""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS meme_votes (
        msg_id INTEGER,
        user_id INTEGER,
        vote INTEGER CHECK(vote IN (-1, 1)),
        PRIMARY KEY (msg_id, user_id))""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS gtn_stats (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        guess INTEGER DEFAULT 0)""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS gtn_save (
        id INTEGER PRIMARY KEY,
        number1 INTEGER DEFAULT NULL,
        number2 INTEGER DEFAULT NULL,
        number INTEGER DEFAULT NULL,
        last_game_message STRING DEFAULT NULL,
        done BOOLEAN DEFAULT FALSE)""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS one_word (
        id INTEGER PRIMARY KEY,
        words STRING DEFAULT NULL,
        last_author_id INTEGER DEFAULT NULL,
        done BOOLEAN DEFAULT FALSE)""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS flag_stats (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        guesses INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0)""")

    async def update_flag_stats(self, user_id, win=True):
        if win:
            await self.exec(
                "UPDATE flag_stats SET wins = wins + 1, guesses = guesses + 1, streak = streak + 1 WHERE user_id = ?",
                (user_id,),
            )
        else:
            await self.exec("UPDATE flag_stats SET guesses = guesses + 1, streak = 0 WHERE user_id = ?", (user_id,))

    async def insert_user(self, table, id_key, user_id):
        await self.exec(f"INSERT OR IGNORE INTO {table} ({id_key}) VALUES (?)", (user_id,))

    async def add_smth(self, table, key, amount, id_key, user_id):
        await self.exec(f"UPDATE {table} SET {key} = {key} + {amount} WHERE {id_key} = ?", (user_id,))

    async def set_smth(self, table, key, amount, id_key, user_id):
        await self.exec(f"UPDATE {table} SET {key} = {amount} WHERE {id_key} = ?", (user_id,))

    async def update_one_word(self, words_json, author_id, game_id, done):
        await self.exec(
            "UPDATE one_word SET words = ?, last_author_id = ?, done = ? WHERE id = ?",
            (words_json, author_id, done, game_id),
        )

    async def new_gtn_game(self, game_id, number1, number2, number, last_game_state):
        await self.exec("INSERT INTO gtn_save (id, number1, number2, number, last_game_message) VALUES (?, ?, ?, ?, ?)", (game_id, number1, number2, number, last_game_state))

    async def get_latest_row(self, table, order_col):
        return await self.one(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT 1")

    async def get_rows(self, table, limit, order_col):
        return await self.all(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT {limit}")

    async def get_finished_games(self):
        return await self.all("SELECT id, words, last_author_id FROM one_word WHERE done = 1 ORDER BY id DESC")

    async def update_row(self, table, key, key2):
        """Update one row"""
        await self.exec(f"UPDATE {table} SET {key} WHERE {key2}")

    async def new_row_one_word(self, game_id, words_json, author_id):
        await self.exec(
            "INSERT INTO one_word (id, words, last_author_id) VALUES (?, ?, ?)", (game_id, words_json, author_id)
        )

    async def add_smth_and_insert(self, table, id_key, user_id, key, amount):
        """Execute multiple queries in one connection."""
        async with self.start() as cursor:
            await cursor.exec(f"INSERT OR IGNORE INTO {table} ({id_key}) VALUES (?)", (user_id,))
            await cursor.exec(f"UPDATE {table} SET {key} = {key} + ? WHERE {id_key} = ?", (amount, user_id))

    async def get_users(self):
        """Return all result rows."""
        return await self.all("SELECT * FROM users")

    async def get_one_row(self, table, key, user_id):
        """Return one result row."""
        return await self.one(f"SELECT * FROM {table} WHERE {key} = ?", (user_id,))


db = UserDB()
