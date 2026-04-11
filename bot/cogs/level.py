import asyncio
import random

import discord
from discord.commands import Option, slash_command
from discord.ext import commands, tasks
from ezcord import log

from bot.db.handler import db
from bot.utils.helpers import load_config
from bot.utils.pagination import EmbedPaginator, build_pages


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

    @staticmethod
    def get_level_progress(xp: int) -> tuple[int, int, int]:
        """Returns (level, current_xp_in_level, xp_needed_for_next_level)"""
        lvl = 1
        amount = 100
        while xp >= amount:
            xp -= amount
            amount += 75
            lvl += 1
        return lvl, xp, amount

    @staticmethod
    def progress_bar(current: int, total: int, length: int = 12) -> str:
        filled = int((current / total) * length)
        return "█" * filled + "░" * (length - filled)

    @staticmethod
    def level_up_cookies(level: int) -> int:
        if level <= 10:
            return 20
        elif level <= 25:
            return 35
        elif level <= 50:
            return 60
        elif level <= 75:
            return 90
        else:
            return 130

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

        await db.new_message(message.author.id, xp)
        log.debug(f"{message.author} + {xp} for message")

        stats = await db.get_level(message.author.id, "level")

        new_xp = stats[2]
        old_level = self.get_level(new_xp - xp)
        new_level = self.get_level(new_xp)
        lvlcookies = Level.level_up_cookies(new_level)

        if old_level != new_level:
            embed = discord.Embed(
                title="Rangaufstieg",
                color=discord.Color.random(),
                description=f"Herzlichen Glückwunsch {message.author.mention} du hast Level **{new_level} ** erreicht! "
                f"Du bekommst **{lvlcookies}** Cookies als Geschenk!",
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)

            await db.add_cookies(message.author.id, lvlcookies)
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
                    if any([member.voice.self_mute, member.voice.self_deaf, member.voice.mute, member.voice.deaf]):
                        continue

                    minutes = 1
                    minutes_xp = self.voice_time_to_xp(minutes)
                    if vc.id in self.halfxpvoicechannel:
                        minutes_xp = minutes_xp // 2

                    stats = await db.get_level(member.id, "voice_level")
                    old_xp = stats[2]

                    await db.add_voice_time(member.id, minutes, minutes_xp)

                    old_level = self.get_level(old_xp)
                    new_level = self.get_level(old_xp + minutes_xp)

                    if old_level != new_level:
                        lvlcookies = Level.level_up_cookies(new_level)
                        await db.add_cookies(member.id, lvlcookies)

                        embed = discord.Embed(
                            title="Voice Rangaufstieg",
                            color=discord.Color.random(),
                            description=f"Herzlichen Glückwunsch du hast Level **{new_level} ** erreicht! "
                            f"Du bekommst **{lvlcookies}** Cookies als Geschenk!",
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        await vc.send(member.mention, embed=embed)

                    await asyncio.sleep(0)

    # --- COMMANDS ---
    @slash_command()
    async def rank(self, ctx, user: Option(discord.Member, required=False)):  # type: ignore
        if not user:
            user = ctx.author
        if user.bot:
            await ctx.respond("Bots haben kein Level :(", ephemeral=True)
            return

        await ctx.defer()
        stats = await db.get_level(user.id, "level")
        voice_stats = await db.get_level(user.id, "voice_level")
        economy = await db.get_level(user.id, "economy")

        xp = stats[2]
        messages = stats[1]
        level, current_xp, xp_needed = self.get_level_progress(xp)
        msg_bar = self.progress_bar(current_xp, xp_needed)

        voice_xp = voice_stats[2]
        voice_minutes = voice_stats[1]
        voice_level, voice_current_xp, voice_xp_needed = self.get_level_progress(voice_xp)
        voice_bar = self.progress_bar(voice_current_xp, voice_xp_needed)

        cookies = economy[1]

        hours, mins = divmod(voice_minutes, 60)
        voice_time_str = f"{hours}h {mins}min" if hours else f"{mins}min"

        embed = discord.Embed(title=f"Rang von {user.display_name}", color=discord.Color.blurple())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(
            name=f"💬 Chat — Level {level}",
            value=f"{msg_bar} `{current_xp}/{xp_needed} XP`\nGesamt: **{xp} XP** • Nachrichten: **{messages}**",
            inline=False,
        )
        embed.add_field(
            name=f"🎙️ Voice — Level {voice_level}",
            value=f"{voice_bar} `{voice_current_xp}/{voice_xp_needed} XP`\n"
            f"Gesamt: **{voice_xp} XP** • Zeit: **{voice_time_str}**",
            inline=False,
        )
        embed.add_field(
            name=f"🍪 Cookies: {cookies}",
            value="",
            inline=False,
        )
        await ctx.respond(embed=embed)

    LEADERBOARD_CATEGORIES = [
        discord.OptionChoice("🍪 Cookies", "cookies"),
        discord.OptionChoice("💬 Nachrichten", "messages"),
        discord.OptionChoice("🎙️ Voice", "voice"),
        discord.OptionChoice("🔢 Guess the Number", "gtn"),
        discord.OptionChoice("🏳️ Flaggenerraten", "flags"),
        discord.OptionChoice("🔢 Counting", "counting"),
    ]

    @slash_command()
    async def leaderboard(self, ctx, categorie: Option(str, choices=LEADERBOARD_CATEGORIES)):  # type: ignore
        await ctx.defer()

        guild_member_ids = {m.id for m in ctx.guild.members}

        async def get_filtered(table, order_col):
            rows = await db.get_leaderboard(table, order_col)
            return [r for r in rows if r[0] in guild_member_ids]

        if categorie == "cookies":
            rows = await get_filtered("economy", "cookies")

            def builder(i, chunk, embed):
                for rank, row in enumerate(chunk, start=i * 10 + 1):
                    member = ctx.guild.get_member(row[0])
                    name = member.display_name if member else f"<@{row[0]}>"
                    embed.add_field(name=f"#{rank} {name}", value=f"**{row[1]}** Cookies", inline=False)

            pages = build_pages(rows, title="🍪 Cookies Leaderboard", builder=builder, chunk_size=10)

        elif categorie == "messages":
            rows = await get_filtered("level", "xp")

            def builder(i, chunk, embed):
                for rank, row in enumerate(chunk, start=i * 10 + 1):
                    member = ctx.guild.get_member(row[0])
                    name = member.display_name if member else f"<@{row[0]}>"
                    lvl = self.get_level(row[2])
                    embed.add_field(
                        name=f"#{rank} {name}",
                        value=f"Level **{lvl}** • **{row[2]}** XP • **{row[1]}** Nachrichten",
                        inline=False,
                    )

            pages = build_pages(rows, title="💬 Nachrichten Leaderboard", builder=builder, chunk_size=10)

        elif categorie == "voice":
            rows = await get_filtered("voice_level", "xp")

            def builder(i, chunk, embed):
                for rank, row in enumerate(chunk, start=i * 10 + 1):
                    member = ctx.guild.get_member(row[0])
                    name = member.display_name if member else f"<@{row[0]}>"
                    lvl = self.get_level(row[2])
                    hours, mins = divmod(row[1], 60)
                    time_str = f"{hours}h {mins}min" if hours else f"{mins}min"
                    embed.add_field(
                        name=f"#{rank} {name}",
                        value=f"Level **{lvl}** • **{row[2]}** XP • {time_str}",
                        inline=False,
                    )

            pages = build_pages(rows, title="🎙️ Voice Leaderboard", builder=builder, chunk_size=10)

        elif categorie == "gtn":
            rows = await get_filtered("gtn_stats", "wins")

            def builder(i, chunk, embed):
                for rank, row in enumerate(chunk, start=i * 10 + 1):
                    member = ctx.guild.get_member(row[0])
                    name = member.display_name if member else f"<@{row[0]}>"
                    winrate = round(row[1] / row[2] * 100) if row[2] > 0 else 0
                    embed.add_field(
                        name=f"#{rank} {name}",
                        value=f"**{row[1]}** Wins • **{row[2]}** Versuche • {winrate}% Winrate",
                        inline=False,
                    )

            pages = build_pages(rows, title="🔢 Guess the Number Leaderboard", builder=builder, chunk_size=10)

        elif categorie == "flags":
            rows = await get_filtered("flag_stats", "wins")

            def builder(i, chunk, embed):
                for rank, row in enumerate(chunk, start=i * 10 + 1):
                    member = ctx.guild.get_member(row[0])
                    name = member.display_name if member else f"<@{row[0]}>"
                    winrate = round(row[1] / row[2] * 100) if row[2] > 0 else 0
                    embed.add_field(
                        name=f"#{rank} {name}",
                        value=f"**{row[1]}** Wins • **{row[2]}** Versuche • Streak: **{row[3]}** • {winrate}% Winrate",
                        inline=False,
                    )

            pages = build_pages(rows, title="🏳️ Flag Stats Leaderboard", builder=builder, chunk_size=10)

        elif categorie == "counting":
            rows = await get_filtered("counting_stats", "counts")

            def builder(i, chunk, embed):
                for rank, row in enumerate(chunk, start=i * 10 + 1):
                    member = ctx.guild.get_member(row[0])
                    name = member.display_name if member else f"<@{row[0]}>"
                    embed.add_field(
                        name=f"#{rank} {name}",
                        value=f"**{row[1]}** Gezählt • **{row[2]}** Fehler",
                        inline=False,
                    )

            pages = build_pages(rows, title="🔢 Counting Leaderboard", builder=builder, chunk_size=10)

        if not pages:
            await ctx.respond("Noch keine Daten vorhanden!", ephemeral=True)
            return

        await EmbedPaginator(pages, loop=True).send(ctx)


def setup(bot):
    bot.add_cog(Level(bot))
