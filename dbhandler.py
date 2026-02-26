import ezcord


class UserDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("data/database.db")

    async def setup(self):
        """Erstellt alle Datenbanktabellen."""
        # Memes
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
        # Guess the Number
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
        # One Word
        await self.exec("""
        CREATE TABLE IF NOT EXISTS one_word (
        id INTEGER PRIMARY KEY,
        words STRING DEFAULT NULL,
        last_author_id INTEGER DEFAULT NULL,
        done BOOLEAN DEFAULT FALSE)""")
        # Flag Stats
        await self.exec("""
        CREATE TABLE IF NOT EXISTS flag_stats (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        guesses INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0)""")
        # TempVoice
        await self.exec("""
        CREATE TABLE IF NOT EXISTS temp_voice (
        channel_id INTEGER PRIMARY KEY,
        owner_id INTEGER NOT NULL,
        panel_msg_id INTEGER DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS temp_voice_bans (
        channel_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (channel_id, user_id))""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS temp_voice_whitelist (
        channel_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (channel_id, user_id))""")

    async def change_owner(self, channel, new_owner):
        await self.exec(
            "UPDATE temp_voice SET owner_id = ? WHERE channel_id = ?",
            (new_owner, channel),
        )

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
        await self.exec(
            "INSERT INTO gtn_save (id, number1, number2, number, last_game_message) VALUES (?, ?, ?, ?, ?)",
            (game_id, number1, number2, number, last_game_state),
        )

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

    # TempVoice Channel CRUD
    async def create_temp_channel(self, channel_id: int, owner_id: int, panel_msg_id: int | None = None) -> None:
        """Speichert einen neuen Temp Channel in der Datenbank."""
        await self.exec(
            "INSERT INTO temp_voice (channel_id, owner_id, panel_msg_id) VALUES (?, ?, ?)",
            (channel_id, owner_id, panel_msg_id),
        )

    async def get_temp_channel(self, channel_id: int):
        """Gibt die DB Zeile eines Temp Channels zurück."""
        return await self.one("SELECT * FROM temp_voice WHERE channel_id = ?", (channel_id,))

    async def get_all_temp_channels(self):
        """Gibt alle gespeicherten Temp Channels zurück (für State Restore)."""
        return await self.all("SELECT * FROM temp_voice")

    async def delete_temp_channel(self, channel_id: int) -> None:
        """Löscht einen Temp Channel aus der Datenbank."""
        await self.exec("DELETE FROM temp_voice WHERE channel_id = ?", (channel_id,))

    async def update_panel_msg(self, channel_id: int, panel_msg_id: int) -> None:
        """Aktualisiert die Panel-Message ID eines Channels."""
        await self.exec(
            "UPDATE temp_voice SET panel_msg_id = ? WHERE channel_id = ?",
            (panel_msg_id, channel_id),
        )

    # TempVoice Bans
    async def add_ban(self, channel_id: int, user_id: int) -> None:
        await self.exec(
            "INSERT OR IGNORE INTO temp_voice_bans (channel_id, user_id) VALUES (?, ?)",
            (channel_id, user_id),
        )

    async def remove_ban(self, channel_id: int, user_id: int) -> None:
        await self.exec(
            "DELETE FROM temp_voice_bans WHERE channel_id = ? AND user_id = ?",
            (channel_id, user_id),
        )

    async def get_bans(self, channel_id: int):
        """Gibt alle gebannten User eines Channels zurück."""
        return await self.all("SELECT * FROM temp_voice_bans WHERE channel_id = ?", (channel_id,))

    async def cleanup_bans(self, channel_id: int) -> None:
        """Löscht alle Bans eines gelöschten Channels."""
        await self.exec("DELETE FROM temp_voice_bans WHERE channel_id = ?", (channel_id,))

    # TempVoice Whitelist
    async def add_whitelist(self, channel_id: int, user_id: int) -> None:
        await self.exec(
            "INSERT OR IGNORE INTO temp_voice_whitelist (channel_id, user_id) VALUES (?, ?)",
            (channel_id, user_id),
        )

    async def remove_whitelist(self, channel_id: int, user_id: int) -> None:
        await self.exec(
            "DELETE FROM temp_voice_whitelist WHERE channel_id = ? AND user_id = ?",
            (channel_id, user_id),
        )

    async def get_whitelist(self, channel_id: int):
        """Gibt alle Whitelist Einträge eines Channels zurück."""
        return await self.all("SELECT * FROM temp_voice_whitelist WHERE channel_id = ?", (channel_id,))

    async def cleanup_whitelist(self, channel_id: int) -> None:
        """Löscht alle Whitelist Einträge eines gelöschten Channels."""
        await self.exec("DELETE FROM temp_voice_whitelist WHERE channel_id = ?", (channel_id,))


db = UserDB()
