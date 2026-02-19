import logging
import random
from zoneinfo import ZoneInfo

import discord
from discord import slash_command
from discord.ext import commands

# VERY EARLY STAGE NOTHING FINAL


async def bot_rps(choice):
    options = ["Stein", "Papier", "Schere"]
    bot_choice = random.choice(options)

    if choice == bot_choice:
        return [choice, bot_choice, 0]
    if (
        (choice == "Stein" and bot_choice == "Schere")
        or (choice == "Papier" and bot_choice == "Stein")
        or (choice == "Schere" and bot_choice == "Papier")
    ):
        return [choice, bot_choice, 1]
    return [choice, bot_choice, 2]


async def bot_rps_result(game, interaction, bot):
    description = f"{bot.user.mention}: {game[1]}\n {interaction.user.mention}: {game[0]}"

    if game[2] == 1:
        embed = discord.Embed(
            title="Du hast Gewonnen!",
            description=description,
            color=discord.Color.green(),
        )
    elif game[2] == 2:
        embed = discord.Embed(
            title="Du hast Verloren!",
            description=description,
            color=discord.Color.red(),
        )
    else:
        embed = discord.Embed(
            title="Unentschieden",
            description=description,
            color=discord.Color.lighter_gray(),
        )
    return embed


async def select_winner(user_selection1, user_selection2):
    draw = discord.Embed(title="Unentschieden")

    if user_selection1 == user_selection2:
        return draw
    if (
        (user_selection1 == "Stein" and user_selection2 == "Schere")
        or (user_selection1 == "Papier" and user_selection2 == "Stein")
        or (user_selection1 == "Schere" and user_selection2 == "Papier")
    ):
        return None
    return None


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.de = ZoneInfo("Europe/Berlin")

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("games.py is ready")

    @slash_command()
    async def rps(self, ctx, enemy: discord.Member = None, rounds: int = 3):
        if enemy is None:
            embed = discord.Embed(
                title="Schere Stein Papier",
                description=f"{ctx.author.mention} vs. {self.bot.user.mention}",
            )
            await ctx.respond(embed=embed, view=BotRPSView(ctx.author, self.bot))
        else:
            embed = discord.Embed(
                title=f"{enemy.name}´s Zug │ Schere Stein Papier",
                description=f"{ctx.author.mention} vs. {enemy.mention}",
            )
            embed.set_footer(text=f"{enemy.name} ist am Zug.")
            await ctx.respond(embed=embed, view=RPSView(ctx.author, enemy))


def setup(bot):
    bot.add_cog(Games(bot))


class RPSView(discord.ui.View):  # code multiplayer rps
    def __init__(self, author, enemy):
        super().__init__()
        self.author = author
        self.enemy = enemy
        self.enemy_choose = None
        self.round = 0

    @discord.ui.button(label="Schere", style=discord.ButtonStyle.primary, emoji="✂️")
    async def button_callback1(self, button, interaction):
        blocked_user = self.enemy if self.round == 0 else self.author

        if interaction.user != blocked_user:
            await interaction.response.send_message(f"{self.enemy.mention} ist im Moment am Zug.", ephemeral=True)
            return

        self.enemy_choose = "Schere"
        self.round = 1
        embed = discord.Embed(
            title=f"{self.author.name}`s Zug │ Schere Stein Papier",
            description=f"{self.author.mention} vs. {self.enemy.mention}",
        )
        embed.set_footer(text=f"{self.author.name} ist am Zug.")

        await interaction.response.edit_message(embed=embed, view=RPSView(self.author, self.enemy))

    @discord.ui.button(label="Stein", style=discord.ButtonStyle.primary, emoji="🪨")
    async def button_callback2(self, button, interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                f"Nur {self.author.mention} kann diesen Button drücken.", ephemeral=True
            )
            return

        game = await bot_rps("Stein")
        embed = await bot_rps_result(game, interaction)

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Papier", style=discord.ButtonStyle.primary, emoji="📰")
    async def button_callback3(self, button, interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                f"Nur {self.author.mention} kann diesen Button drücken.", ephemeral=True
            )
            return

        game = await bot_rps("Papier")
        embed = await bot_rps_result(game, interaction)

        await interaction.response.edit_message(embed=embed, view=None)


# ---


class BotRPSView(discord.ui.View):
    def __init__(self, author, bot):
        super().__init__()
        self.author = author
        self.bot = bot

    @discord.ui.button(label="Schere", style=discord.ButtonStyle.primary, emoji="✂️")
    async def button_callback1(self, button, interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                f"Nur {self.author.mention} kann diesen Button drücken.", ephemeral=True
            )
            return

        game = await bot_rps("Schere")
        embed = await bot_rps_result(game, interaction, self.bot)

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Stein", style=discord.ButtonStyle.primary, emoji="🪨")
    async def button_callback2(self, button, interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                f"Nur {self.author.mention} kann diesen Button drücken.", ephemeral=True
            )
            return

        game = await bot_rps("Stein")
        embed = await bot_rps_result(game, interaction, self.bot)

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Papier", style=discord.ButtonStyle.primary, emoji="📰")
    async def button_callback3(self, button, interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                f"Nur {self.author.mention} kann diesen Button drücken.", ephemeral=True
            )
            return

        game = await bot_rps("Papier")
        embed = await bot_rps_result(game, interaction, self.bot)

        await interaction.response.edit_message(embed=embed, view=None)
