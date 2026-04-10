import random
from datetime import UTC, datetime, time, timedelta

import discord
from discord import slash_command
from ezcord import log
from ezcord.internal.dc import commands

from bot.db.handler import db


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("economy.py is ready")

    @slash_command()
    async def daily(self, ctx):
        streak_data = await db.get_one_row("daily", "user_id", ctx.author.id)
        streak = streak_data[1] if streak_data else 0
        base = random.randint(20, 35)
        streak_bonus = max(0, min((streak - 1) * 3, 45))
        cookies = base + streak_bonus
        
        data = await db.redeem_daily(ctx.author.id, cookies)
        typ = data[0]
        streak = data[1]
        claims = data[2]

        if typ == 0:  # Daily wurde schon abgeholt.
            last_claim = data[3]
            timestamp = datetime.combine(last_claim, time.min, tzinfo=UTC) + timedelta(days=1)
            embed = discord.Embed(
                title="⏳ Bereits abgeholt!",
                description=(
                    "Du hast deine Tägliche Belohnung heute bereits kassiert.\n"
                    f"Komm <t:{int(timestamp.timestamp())}:R> wieder!"
                ),
                color=discord.Color.light_gray(),
            )
            embed.set_footer(text=f"🔥 Streak: {streak} Tage  •  📦 Gesamt: {claims}x abgeholt")
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.respond(embed=embed, ephemeral=True)

        elif typ == 1:  # Daily abgeholt, Streak verlängert.
            embed = discord.Embed(
                title="🍪 Daily kassiert!",
                description=(
                    f"Du hast **{cookies} Cookies** erhalten!\n\n"
                    f"🔥 **Streak verlängert!** Du bist jetzt seit **{streak} Tagen** dabei."
                ),
                color=discord.Color.orange(),
            )
            embed.add_field(name="🍪 Cookies erhalten", value=f"`{cookies}`", inline=True)
            embed.add_field(name="🔥 Streak", value=f"`{streak} Tage`", inline=True)
            embed.add_field(name="📦 Gesamt abgeholt", value=f"`{claims}x`", inline=True)
            embed.set_footer(text="Komm morgen wieder, um deinen Streak zu verlängern!")
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.respond(embed=embed)

        else:  # Daily abgeholt, Streak unterbrochen.
            embed = discord.Embed(
                title="🍪 Daily kassiert!",
                description=(
                    f"Du hast **{cookies} Cookies** erhalten!\n\n"
                    f"💔 **Streak verloren!** Du hast zu lange eine Pause eingelegt.\n"
                    f"Dein Streak startet jetzt neu bei **1 Tag**."
                ),
                color=discord.Color.red(),
            )
            embed.add_field(name="🍪 Cookies erhalten", value=f"`{cookies}`", inline=True)
            embed.add_field(name="🔥 Streak", value="`1 Tag`", inline=True)
            embed.add_field(name="📦 Gesamt abgeholt", value=f"`{claims}x`", inline=True)
            embed.set_footer(text="Komm morgen wieder, um deinen Streak aufzubauen!")
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Economy(bot))