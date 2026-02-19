# I am not proud of it, but it works, and never change a running system or smth like that

# needs polish
import configparser
import logging
from zoneinfo import ZoneInfo

import aiosqlite
from discord.ext import commands


async def fetch_meme_msg_ids(db_path: str, message_id: int) -> list[int]:
    async with (
        aiosqlite.connect(db_path) as db,
        db.execute("SELECT 1 FROM memes WHERE msg_id = ?", (message_id,)) as cursor,
    ):
        exists = await cursor.fetchone()
        return exists[0] if exists else None


class MemeVoting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = "data/database.db"
        self.de = ZoneInfo("Europe/Berlin")
        self.parser = configparser.ConfigParser()
        self.parser.read("config.cfg")
        self.channel = int(self.parser["CHANNELS"]["memes"])

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("memes.py is ready")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.channel.id != self.channel:
            return
        if len(message.attachments) > 1:
            return

        if message.attachments:
            async with aiosqlite.connect(self.database) as db:
                await db.execute(
                    "INSERT INTO memes (user_id, msg_id, meme_url, meme_txt) VALUES (?, ?, ?, ?)",
                    (
                        message.author.id,
                        message.id,
                        message.attachments[0].url,
                        message.content,
                    ),
                )
                await db.commit()
                await message.add_reaction("⬆️")
                await message.add_reaction("⬇️")
                logging.info("user sent a meme")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        if payload.channel_id != self.channel:
            return

        if payload.emoji.name in ("⬆️", "⬇️"):
            vote = -1 if payload.emoji.name == "⬇️" else 1

            async with aiosqlite.connect(self.database) as db:
                try:
                    await db.execute(
                        "INSERT INTO meme_votes (msg_id, user_id, vote) VALUES (?, ?, ?)",
                        (payload.message_id, payload.user_id, vote),
                    )
                except aiosqlite.IntegrityError:
                    return

                if not await fetch_meme_msg_ids(self.database, payload.message_id):
                    return

                logging.info("up- or downvote on a meme")

                await db.execute(
                    "UPDATE memes SET votes = votes + ? WHERE msg_id = ?",
                    (vote, payload.message_id),
                )
                await db.commit()
                # if reactions are changed to quickly it breaks, just do everything over the db

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        if payload.channel_id != self.channel:
            return

        if payload.emoji.name in ("⬆️", "⬇️"):
            if not await fetch_meme_msg_ids(self.database, payload.message_id):
                return

            async with aiosqlite.connect(self.database) as db:
                await db.execute(
                    "DELETE FROM meme_votes WHERE msg_id = ? AND user_id = ?",
                    (payload.message_id, payload.user_id),
                )

                logging.info("removed up- or downvote on a meme")

                vote = 1 if payload.emoji.name == "⬇️" else -1

                await db.execute(
                    "UPDATE memes SET votes = votes + ? WHERE msg_id = ?",
                    (vote, payload.message_id),
                )
                await db.commit()
                print(payload.emoji.name)


def setup(bot):
    bot.add_cog(MemeVoting(bot))
