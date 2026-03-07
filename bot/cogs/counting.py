import asyncio

import discord
import simpleeval
from discord.ext import commands
from ezcord import log

from bot.db import handler
from bot.utils.helpers import load_config


class CountingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lock = asyncio.Lock()

        self.channel_id = load_config("CHANNELS", "counting", "int")

        self.count = 0
        self.previous_author_id = None

    @commands.Cog.listener()
    async def on_ready(self):
        await handler.db.init_counting()

        state = await handler.db.get_counting_state()
        if state:
            self.count = state[0]

        if self.count == 0:
            await self.bot.get_channel(self.channel_id).send(f"**0** | Highscore: {state[1]}")

        log.info(f"counting.py ready, the count is now on {self.count}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.channel_id or message.channel.id != self.channel_id or message.author.bot:
            return

        async with self.lock:
            content = message.content.strip()

            try:
                result = simpleeval.simple_eval(content)
                if not isinstance(result, (int, float)):
                    return
                result = int(result)
            except:
                return

            if message.author.id == self.previous_author_id:
                embed = discord.Embed(
                    title="Verkackt!",
                    description=f"{message.author.mention}, du darfst nicht zweimal hintereinander zählen!",
                    color=discord.Color.red(),
                )
                await self.fail_game(message, embed)
                return

            if result == self.count + 1:
                self.count += 1
                self.previous_author_id = message.author.id
                await handler.db.update_counting(self.count)
                await message.add_reaction("✅")
            else:
                embed = discord.Embed(
                    title="Verkackt!",
                    description=f"{message.author.mention} hat die falsche Zahl geschrieben!",
                    color=discord.Color.red(),
                )
                await self.fail_game(message, embed)

    async def fail_game(self, message, embed):
        highscore = await handler.db.get_counting_state()

        self.count = 0
        self.previous_author_id = None
        await handler.db.update_counting(0)

        await message.add_reaction("❌")
        await message.channel.send(embed=embed)
        await message.channel.send(f"**0** | Highscore: {highscore[1]}")


def setup(bot):
    bot.add_cog(CountingCog(bot))
