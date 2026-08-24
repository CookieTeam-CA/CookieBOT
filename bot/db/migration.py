import ezcord

CURRENT_SCHEMA_VERSION = 1


class UserDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("data/database.db")


    async def migrate(self):
        table = await self.one("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'")

        if table is None:
            counting = await self.one("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'counting'")

            if counting is None:
                await self.exec("CREATE TABLE schema_version (version INTEGER NOT NULL)")
                await self.exec(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    CURRENT_SCHEMA_VERSION,
                )
                return

            await self.exec("CREATE TABLE schema_version (version INTEGER NOT NULL)")
            await self.exec("INSERT INTO schema_version (version) VALUES (0)")

            version = 0

        else:
            row = await self.one("SELECT version FROM schema_version LIMIT 1")
            version = row[0] if row else 0

        if version < 1:
            await self.exec("ALTER TABLE counting ADD COLUMN last_message_id INTEGER")
            await self.exec("UPDATE schema_version SET version = 1")

            version = 1


db = UserDB()
