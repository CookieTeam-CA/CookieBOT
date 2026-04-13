import asyncio
import json
import time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from ezcord import log
from ezcord.internal.dc import slash_command

from bot.db.handler import db
from bot.utils.helpers import load_config, safe_delete
from bot.utils.pagination import EmbedPaginator, build_pages


class OneWordChallenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.de = ZoneInfo("Europe/Berlin")

        self.channel = load_config("CHANNELS", "one_word", "int")

        self.id = None
        self.words = []
        self.last_author = None

    @commands.Cog.listener()
    async def on_ready(self):
        last_game_state = await db.get_latest_row("one_word", "id")

        if last_game_state and last_game_state[3] == 0:
            self.id = last_game_state[0]
            self.last_author = last_game_state[2]

            try:
                self.words = json.loads(last_game_state[1]) if last_game_state[1] else []
            except (json.JSONDecodeError, TypeError):
                log.warning("Game save couldn't load. Starting new.")
                self.words = []

            log.debug("one_word restored last game state")
        else:
            log.debug("one_word no active game found.")

        log.info("one_word.py is ready")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != self.channel or message.author.bot:
            return
        if self.last_author == message.author.id:
            msg = await message.reply(
                "Du darfst nicht 2 Wörter hintereinander schreiben.",
                mention_author=False,
            )
            await safe_delete(message)
            await asyncio.sleep(5)
            await safe_delete(msg)
            return

        content = message.content.strip()

        if len(content.split()) == 1:
            self.words.append(content)
            self.last_author = message.author.id

            if self.id is None:
                self.id = int(time.time() * 1000)
                await db.new_row_one_word(self.id, json.dumps(self.words), self.last_author)
            else:
                await db.update_one_word(json.dumps(self.words), self.last_author, self.id, 0)

            await message.add_reaction("✅")

            if content.endswith((".", "?", "!")):
                embed = discord.Embed(
                    title="Der Fertige Satz ist:", description=(" ".join(self.words)), color=discord.Color.random()
                )
                embed.set_footer(text="Nutze /one_word_list um vorherige Sätze anzuschauen!")
                await message.channel.send(embed=embed)
                await db.update_one_word(json.dumps(self.words), self.last_author, self.id, 1)
                self.id = None
                self.words = []
        else:
            msg = await message.reply("Du darfst nur ein Wort schreiben.", mention_author=False)
            await safe_delete(message)
            await asyncio.sleep(5)
            await safe_delete(msg)

    @slash_command()
    async def one_word_list(self, ctx):
        log.info(f"{ctx.author} used /one_word_list")
        await ctx.defer()
        data = await db.get_finished_games()

        if not data:
            return await ctx.respond("Es wurden noch keine Sätze vervollständigt.", ephemeral=True)

        def builder(i, chunk, embed):
            for row in chunk:
                try:
                    sentence = " ".join(json.loads(row[1]) if row[1] else [])
                except json.JSONDecodeError:
                    sentence = "*Fehler beim Laden*"
                embed.add_field(
                    name=f"Satz #{row[0]}",
                    value=f"💬 {sentence}\n🏁 Beendet von: <@{row[2]}>",
                    inline=False,
                )

        pages = build_pages(data, title="📚 One Word Verlauf", builder=builder)
        await EmbedPaginator(pages).send(ctx)


def setup(bot):
    bot.add_cog(OneWordChallenge(bot))
