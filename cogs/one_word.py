import asyncio
import configparser
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands


class OneWordChallange(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.de = ZoneInfo("Europe/Berlin")
        self.parser = configparser.ConfigParser()
        self.parser.read("config.cfg")
        self.channel = int(self.parser["CHANNELS"]["one_word"])
        self.words = []
        self.last_author = None

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("one_word.py is ready")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.channel.id != self.channel:
            return
        if self.last_author == message.author:
            msg = await message.reply(
                "Du darfst nicht 2 Wörter hintereinander schreiben.",
                mention_author=False,
            )
            await message.delete()
            await asyncio.sleep(5)
            await msg.delete()
            return

        if len(message.content.split()) == 1:
            self.words.append(message.content)
            self.last_author = message.author
            await message.add_reaction("✅")
        else:
            msg = await message.reply("Du darfst nur ein Wort schreiben.", mention_author=False)
            await message.delete()
            await asyncio.sleep(5)
            await msg.delete()

        if message.content.strip().endswith("."):
            embed = discord.Embed(
                title="Der Fertige Satz ist:",
                description=(" ".join(self.words)),
                color=discord.Color.random(),
                timestamp=datetime.now(tz=self.de),
            )
            await message.channel.send(embed=embed)
            self.words = []


def setup(bot):
    bot.add_cog(OneWordChallange(bot))
