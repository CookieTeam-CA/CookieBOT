import configparser
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import aiosqlite
import discord
from discord.ext import commands
from ezcord import log


class GuessNumber(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = "data/database.db"
        self.de = ZoneInfo("Europe/Berlin")
        self.parser = configparser.ConfigParser()
        self.parser.read("config.cfg")
        try:
            self.channel = int(self.parser["CHANNELS"]["guess_number_channel"])
        except (KeyError, ValueError):
            log.error("GuessNumberChannel ID not found in config.cfg!")
            self.channel = None

        self.number = None
        self.number1 = None
        self.number2 = None
        self.last_game_message = None
        # maybe noch in datenbank diese daten speichern damit auch nach restart das game noch gleich ist

    async def new_game(self):
        difficulties = {
            "einfach": (1, 25, 26, 50, discord.Color.green()),
            "mittel": (1, 50, 51, 100, discord.Color.yellow()),
            "schwer": (1, 100, 101, 200, discord.Color.red()),
        }
        difficulty = random.choice(list(difficulties.keys()))
        (one1, two1, one2, two2, color) = difficulties[difficulty]

        self.number1 = random.randint(one1, two1)
        self.number2 = random.randint(one2, two2)
        self.number = random.randint(self.number1, self.number2)

        embed = discord.Embed(
            title="Guess the Number",
            description=f"Die Zahl die zu erraten ist befindet sich **zwischen {self.number1} und {self.number2}**.\n "
            f"Die Schwierigkeit ist **{difficulty}**.",
            color=color,
            timestamp=datetime.now(tz=self.de),
        )
        self.last_game_message = await self.bot.get_channel(self.channel).send(embed=embed)
        await discord.Message.pin(self.last_game_message, reason="Guess the Number Game")

        async for message in self.bot.get_channel(self.channel).history(limit=1):
            if message.type == discord.MessageType.pins_add:
                await message.delete()

        log.info(f"Guess Number was sent, the number is {self.number}.")

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("guess_number.py is ready")
        await self.new_game()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != self.channel:
            return

        try:
            guess = int(message.content)
        except ValueError:
            return

        async with aiosqlite.connect(self.db) as db:
            await db.execute(
                "INSERT OR IGNORE INTO gtn_stats (user_id) VALUES (?)",
                (message.author.id,),
            )
            await db.execute(
                "UPDATE gtn_stats SET guess = guess + 1 WHERE user_id = ?",
                (message.author.id,),
            )
            await db.commit()

        if guess == self.number:
            async with aiosqlite.connect(self.db) as db:
                await db.execute(
                    "UPDATE gtn_stats SET wins = wins + 1 WHERE user_id = ?",
                    (message.author.id,),
                )
                await db.commit()

            async with (
                aiosqlite.connect(self.db) as db,
                db.execute(
                    "SELECT wins, guess FROM gtn_stats WHERE user_id = ?",
                    (message.author.id,),
                ) as cursor,
            ):
                result = await cursor.fetchone()
                print(f"{result[0]} / {result[1]}")
                wins = result[0] + 1
                guesses = result[1]
                winrate = (wins / guesses) * 100 if guesses > 0 else 0

            embed = discord.Embed(
                title="RICHTIG!",
                description=f"{message.author.mention} hat die Zahl **{self.number}** geschrieben und lag richtig.",
                color=discord.Color.green(),
                timestamp=datetime.now(tz=self.de),
            )
            embed.set_footer(text=f"{message.author.display_name} hat eine Gewinnchance von {round(winrate, 2)}%.")
            await self.bot.get_channel(self.channel).send(embed=embed)
            await message.add_reaction("✅")
            await discord.Message.unpin(self.last_game_message, reason="Guess the Number Game")
            await self.new_game()
            log.info(f"{message.author} wrote the correct number {self.number}")
            # jetzt noch kekse geben
        else:
            await message.add_reaction("❌")
            chance = random.randint(1, 5)
            if chance == 1:
                if self.number1 <= guess <= self.number2:
                    if guess > self.number:
                        await message.reply("Die gesuchte Zahl ist kleiner.", mention_author=False)
                    else:
                        await message.reply("Die gesuchte Zahl ist größer.", mention_author=False)
                else:
                    await message.reply(
                        f"Deine Zahl liegt nicht in der angegebenen Zahlen spanne. "
                        f"Die gesuchte Zahl liegt zwischen **{self.number1} und {self.number2}**.",
                        mention_author=False,
                    )


def setup(bot):
    bot.add_cog(GuessNumber(bot))
