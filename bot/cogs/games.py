import asyncio
import random

from discord import Color, Embed, Option
from discord.ext import commands
from ezcord import log
from ezcord.internal.dc import slash_command

from bot.db.handler import db


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("one_word.py is ready")

    @slash_command()
    async def coinflip(self, ctx, coin: Option(str, required=True, choices=["Kopf", "Zahl"]), cookies: int):  # type: ignore
        if cookies <= 0:
            return await ctx.respond("Du musst mindestens 1 Cookie setzen.", ephemeral=True)

        bank = await db.get_cookies(ctx.author.id)
        if bank < cookies:
            return await ctx.respond(
                f"Du hast nicht genügend Cookies. (Guthaben: **{bank}** Cookies)", ephemeral=True
            )

        msg = await ctx.respond("🪙 Die Münze wird geworfen...")
        result = random.choice(["Kopf", "Zahl"])
        choice = "heads" if coin == "Kopf" else "tails"
        await asyncio.sleep(0.5)

        won = coin == result

        if won:
            await db.coinflip_win(ctx.author.id, choice, cookies)
            await db.add_cookies(ctx.author.id, cookies)
        else:
            await db.coinflip_loss(ctx.author.id, choice, cookies)
            await db.remove_cookies(ctx.author.id, cookies)

        stats = await db.get_coinflip_stats(ctx.author.id)
        new_balance = await db.get_cookies(ctx.author.id)

        # stats: [user_id, heads, tails, heads_wins, tails_wins, current_streak, best_streak, cookies_loss, cookies_won]
        total_flips = stats[1] + stats[2]
        total_wins = stats[3] + stats[4]
        winrate = round(total_wins / total_flips * 100) if total_flips > 0 else 0
        net_profit = stats[8] - stats[7]
        net_str = f"+{net_profit}" if net_profit >= 0 else str(net_profit)

        if won:
            embed = Embed(title=f"Gewonnen! {result}", color=Color.green())
            embed.add_field(name="Gewinn", value=f"+**{cookies}** Cookies", inline=True)
            embed.add_field(name="Guthaben", value=f"**{new_balance}** Cookies", inline=True)
            embed.add_field(name="🔥 Streak", value=f"**{stats[5]}**", inline=True)
            embed.add_field(name="🏆 Best Streak", value=f"**{stats[6]}**", inline=True)
            embed.add_field(name="📊 Winrate", value=f"**{winrate}%**", inline=True)
            embed.add_field(name="💰 Profit", value=f"**{net_str}** Cookies", inline=True)
        else:
            embed = Embed(title=f"Verloren! {result}", color=Color.red())
            embed.add_field(name="Verlust", value=f"-**{cookies}** Cookies", inline=True)
            embed.add_field(name="Guthaben", value=f"**{new_balance}** Cookies", inline=True)
            embed.add_field(name="🔥 Streak", value="**0**", inline=True)
            embed.add_field(name="🏆 Best Streak", value=f"**{stats[6]}**", inline=True)
            embed.add_field(name="📊 Winrate", value=f"**{winrate}%**", inline=True)
            embed.add_field(name="💰 Profit", value=f"**{net_str}** Cookies", inline=True)

        await msg.edit(content=None, embed=embed)


def setup(bot):
    bot.add_cog(Games(bot))
