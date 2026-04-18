from datetime import UTC, datetime, timedelta
from typing import Literal

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
        # Counting
        await self.exec("""
        CREATE TABLE IF NOT EXISTS counting (
        id INTEGER PRIMARY KEY,
        count INTEGER DEFAULT 0,
        highscore INTEGER DEFAULT 0)""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS counting_stats (
        user_id INTEGER PRIMARY KEY,
        counts INTEGER DEFAULT 0,
        fails INTEGER DEFAULT 0)""")
        # Reactionrole
        await self.exec("""
        CREATE TABLE IF NOT EXISTS reactionroles (
        msg_id INTEGER PRIMARY KEY,
        emoji STRING DEFAULT NULL,
        role_id INTEGER NOT NULL)""")
        # Level
        await self.exec("""
        CREATE TABLE IF NOT EXISTS level (
        user_id INTEGER PRIMARY KEY,
        msg_count INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0)""")
        await self.exec("""
        CREATE TABLE IF NOT EXISTS voice_level (
        user_id INTEGER PRIMARY KEY,
        minutes INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0)""")
        # Economy
        await self.exec("""
        CREATE TABLE IF NOT EXISTS economy (
        user_id INTEGER PRIMARY KEY,
        cookies INTEGER DEFAULT 0)""")
        # Daily
        await self.exec("""
        CREATE TABLE IF NOT EXISTS daily (
        user_id INTEGER PRIMARY KEY,
        streak INTEGER DEFAULT 0,
        claimed INTEGER DEFAULT 0,
        last_claimed TEXT DEFAULT '1970-01-01')""")
        # Settings
        await self.exec("""
        CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER PRIMARY KEY,
        dm INTEGER DEFAULT 1,
        ping INTEGER DEFAULT 1)""")  # 1 = ping bzw dm senden
        # Coinflip
        await self.exec("""
        CREATE TABLE IF NOT EXISTS coinflip (
        user_id INTEGER PRIMARY KEY,
        heads INTEGER DEFAULT 0,
        tails INTEGER DEFAULT 0,
        heads_wins INTEGER DEFAULT 0,
        tails_wins INTEGER DEFAULT 0,
        current_streak INTEGER DEFAULT 0,
        best_streak INTEGER DEFAULT 0,
        cookies_loss INTEGER DEFAULT 0,
        cookies_won INTEGER DEFAULT 0)""")  # loses = heads + tails - head_wins - tails_wins

    ### --- COINFLIP ---
    async def coinflip_win(self, user_id, choice: Literal["heads", "tails"], cookies_bet: int):
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO coinflip (user_id) VALUES (?)", (user_id,))
            await cursor.exec(
                f"UPDATE coinflip SET {choice} = {choice} + 1, {choice}_wins = {choice}_wins + 1, "
                "current_streak = current_streak + 1, cookies_won = cookies_won + ?, best_streak = MAX(best_streak, "
                "current_streak + 1) WHERE user_id = ?",
                (cookies_bet, user_id),
            )

    async def coinflip_loss(self, user_id, choice: Literal["heads", "tails"], cookies_bet: int):
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO coinflip (user_id) VALUES (?)", (user_id,))
            await cursor.exec(
                f"UPDATE coinflip SET {choice} = {choice} + 1, current_streak = 0, cookies_loss = cookies_loss + ? "
                "WHERE user_id = ?",
                (cookies_bet, user_id),
            )

    async def get_coinflip_stats(self, user_id):
        return await self.one("SELECT * FROM coinflip WHERE user_id = ?", (user_id,))

    ### --- SETTINGS ---
    async def change_setting(self, user_id, setting, to):  # 0 nicht geändert da schon so ist, 1 = erfolgreich geändert
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO settings (user_id) VALUES (?)", (user_id,))
            current_setting = await cursor.one(f"SELECT {setting} FROM settings WHERE user_id = ?", (user_id,))
            if current_setting == to:
                return 0

            await cursor.exec(f"UPDATE settings SET {setting} = ? WHERE user_id = ?", (to, user_id))
            return 1

    async def get_setting(self, user_id, setting):
        return await self.one(f"SELECT {setting} FROM settings WHERE user_id = ?", (user_id,))

    ### --- DAILY ---
    async def redeem_daily(self, user_id, cookies):
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO daily (user_id) VALUES (?)", (user_id,))
            daily_stats = await cursor.one(
                "SELECT last_claimed, streak, claimed FROM daily WHERE user_id = ?", (user_id,)
            )
            streak = daily_stats[1]
            claimed = daily_stats[2]
            last_claimed = datetime.fromisoformat(daily_stats[0]).date()
            today = datetime.now(UTC).date()

            if last_claimed == today:
                return 0, streak, claimed, last_claimed
            elif last_claimed == today - timedelta(days=1):
                await cursor.exec(
                    "UPDATE daily SET last_claimed = ?, streak = streak + 1, claimed = claimed + 1 WHERE user_id = ?",
                    (today.isoformat(), user_id),
                )
                await cursor.exec("UPDATE economy SET cookies = cookies + ? WHERE user_id = ?", (cookies, user_id))
                return 1, streak + 1, claimed + 1, last_claimed
            else:
                await cursor.exec(
                    "UPDATE daily SET last_claimed = ?, streak = 1, claimed = claimed + 1 WHERE user_id = ?",
                    (today.isoformat(), user_id),
                )
                await cursor.exec("UPDATE economy SET cookies = cookies + ? WHERE user_id = ?", (cookies, user_id))
                if last_claimed.isoformat() == "1970-01-01":
                    return 1, 1, claimed + 1, last_claimed
                return 2, 1, claimed + 1, last_claimed

    ### --- ECONOMY ---
    async def add_cookies(self, user_id, cookies):
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            await cursor.exec("UPDATE economy SET cookies = cookies + ? WHERE user_id = ?", (cookies, user_id))

    async def remove_cookies(self, user_id, cookies):
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            result = await cursor.exec(
                "UPDATE economy SET cookies = cookies - ? WHERE user_id = ? AND cookies >= ?",
                (cookies, user_id, cookies),
            )

            return result.rowcount  # 1 = erfolgreich, 0 = nicht genug cookies

    async def get_cookies(self, user_id):
        res = await self.one("SELECT cookies FROM economy WHERE user_id = ?", (user_id,))
        return res if res else 0

    ### --- LEVELS ---
    async def add_voice_time(self, user_id, minutes, xp):
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO voice_level (user_id) VALUES (?)", (user_id,))
            await cursor.exec(
                "UPDATE voice_level SET minutes = minutes + ?, xp = xp + ? WHERE user_id = ?", (minutes, xp, user_id)
            )

    async def new_message(self, user_id, xp):
        async with self.start() as cursor:
            await cursor.exec("INSERT OR IGNORE INTO level (user_id) VALUES (?)", (user_id,))
            await cursor.exec("UPDATE level SET xp = xp + ? WHERE user_id = ?", (xp, user_id))
            await cursor.exec("UPDATE level SET msg_count = msg_count + 1 WHERE user_id = ?", (user_id,))

    async def get_level(self, user_id, table: Literal["level", "voice_level", "economy"]):
        async with self.start() as cursor:
            await cursor.exec(f"INSERT OR IGNORE INTO {table} (user_id) VALUES (?)", (user_id,))
            return await cursor.one(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,))

    async def get_leaderboard(self, table: str, order_col: str, limit: int = 100):
        return await self.all(f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT ?", (limit,))

    ### --- REACTIONROLES ---
    async def create_rr(self, msg_id, emoji, role_id):
        await self.exec("INSERT INTO reactionroles (msg_id, emoji, role_id) VALUES (?, ?, ?)", (msg_id, emoji, role_id))

    async def get_reactionroles(self):
        return await self.all("SELECT * FROM reactionroles")

    async def get_specific_reactionrole(self, msg_id, emoji):
        return await self.one("SELECT * FROM reactionroles WHERE msg_id = ? and emoji = ?", (msg_id, emoji))

    async def delete_rr(self, msg_id, emoji):
        await self.exec("DELETE FROM reactionroles WHERE msg_id = ? and emoji = ?", (msg_id, emoji))

    ### --- COUNTING ---
    async def init_counting(self):
        await self.exec("INSERT OR IGNORE INTO counting (id, count, highscore) VALUES (1, 0, 0)")

    async def get_counting_state(self):
        return await self.one("SELECT count, highscore FROM counting WHERE id = 1")

    async def update_counting(self, count, user_id, fail=0):
        await self.exec("UPDATE counting SET count = ?, highscore = MAX(highscore, ?) WHERE id = 1", (count, count))
        await self.exec(
            "INSERT INTO counting_stats (user_id, counts, fails) VALUES (?, 1, ?) ON CONFLICT(user_id) DO "
            "UPDATE SET counts = counts + 1, fails = fails + ? WHERE user_id = ?",
            (user_id, fail, fail, user_id),
        )

    ### --- OTHER ---

    async def insert_smth(self, table, key, value):
        await self.exec(f"INSERT INTO {table} ({key}) VALUES (?)", (value,))

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

    async def set_smth_without_where(self, table, key, amount):
        await self.exec(f"UPDATE {table} SET {key} = {amount}")

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
