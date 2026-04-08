import asyncio
import random

import discord
from discord.ext import commands, tasks
from ezcord import log

from bot.db import handler
from bot.utils.helpers import load_config


class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.halfxpchannel = load_config("ECONOMY", "half_xp_channels", "list")
        self.noxpchannel = load_config("ECONOMY", "no_xp_channels", "list")
        self._cooldowns = {}

        self.voice_tick.start()
        self.noxpvoicechannel = load_config("ECONOMY", "no_xp_voicechannels", "list")
        self.halfxpvoicechannel = load_config("ECONOMY", "half_xp_voicechannels", "list")
        self.voicelvl_announce = load_config("ECONOMY", "voice_lvl_annouce_channel", "int")
        self.voice_xp_per_minute = random.randint(3, 7)

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
        return 100 + 75 * lvl

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id in self.noxpchannel:
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

    # --- VOICE XP ---
    def voice_time_to_xp(self, minutes: int) -> int:
        """Time -> XP"""
        return minutes * self.voice_xp_per_minute

    def voice_xp_to_next_level(self, xp: int) -> int:
        """XP to next Level"""
        lvl = Level.get_level(xp)
        return 100 + 75 * (lvl - 1)

    @tasks.loop(minutes=1)
    async def voice_tick(self):
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                if vc.id in self.noxpvoicechannel:
                    continue
                for member in vc.members:
                    if member.bot:
                        continue

                    minutes = 1
                    minutes_xp = self.voice_time_to_xp(minutes)
                    if vc.id in self.halfxpvoicechannel:
                        minutes_xp = minutes_xp // 2

                    stats = await handler.db.get_voice_stats(member.id)
                    old_xp = stats[2]

                    await handler.db.add_voice_time(member.id, minutes, minutes_xp)
                    log.debug(f"{member} + {minutes_xp} for 1 min in talk")

                    old_level = self.get_level(old_xp)
                    new_level = self.get_level(old_xp + minutes_xp)

                    if old_level != new_level:
                        lvlcookies = new_level * 5
                        await handler.db.add_cookies(member.id, lvlcookies)

                        embed = discord.Embed(
                            title="Voice Rangaufstieg",
                            color=discord.Color.random(),
                            description=f"Herzlichen Glückwunsch {member.id} du hast Level **{new_level} ** erreicht! "
                            f"Du bekommst **{lvlcookies}** Cookies als Geschenk!",
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await self.bot.get_channel(self.voicelvl_announce).send(embed=embed)

                    await asyncio.sleep(0)


def setup(bot):
    bot.add_cog(Level(bot))
