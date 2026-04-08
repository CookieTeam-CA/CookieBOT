import random

import discord
from discord.ext import commands
from ezcord import log

from bot.db import handler
from bot.utils.helpers import load_config


class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.halfxpchannel = load_config("ECONOMY", "half_xp_channels", "list")
        self._cooldowns = {}

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("level.py is ready")

    @staticmethod
    def get_level(xp):
        lvl = 1
        amount = 100

        while True:
            xp -= amount
            if xp < 0:
                return lvl
            lvl += 1
            amount += 75

    @staticmethod
    def xp_to_next_level(xp):
        lvl = Level.get_level(xp)
        return 175 + (75 * lvl)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        now = discord.utils.utcnow().timestamp()
        last = self._cooldowns.get(message.author.id, 0)
        if now - last < 5:
            return
        self._cooldowns[message.author.id] = now

        xp = random.randint(15, 25)
        if message.channel.id in self.halfxpchannel:
            xp = xp // 2

        await handler.db.new_message(message.author.id, xp)
        log.debug(f"{message.author} + {xp} for message")

        new_xp = await handler.db.get_xp(message.author.id)
        old_level = self.get_level(new_xp - xp)
        new_level = self.get_level(new_xp)
        lvlcookies = new_level * 5

        if old_level != new_level:
            embed = discord.Embed(
                title="Rangaufstieg",
                color=discord.Color.random(),
                description=f"Herzlichen Glückwunsch {message.author.mention} du hast Level **{new_level} ** erreicht! "
                f"Du bekommst **{lvlcookies}** Cookies als Geschenk!",
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)

            await handler.db.add_cookies(message.author.id, lvlcookies)
            await message.channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Level(bot))
