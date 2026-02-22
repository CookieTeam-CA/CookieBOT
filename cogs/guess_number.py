import configparser
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from ezcord import log

import dbhandler
import utils


class GuessNumber(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.de = ZoneInfo("Europe/Berlin")
        self.parser = configparser.ConfigParser()
        self.parser.read("config.cfg")
        try:
            self.channel = int(self.parser["CHANNELS"]["guess_number_channel"])
        except (KeyError, ValueError):
            log.error("GuessNumberChannel ID not found in config.cfg!")
            self.channel = None

        self.id = None
        self.number = None
        self.number1 = None
        self.number2 = None
        self.last_game_message = None
        self.race_condition = None

    async def new_game(self):
        difficulties = {
            "einfach": (1, 25, 26, 50, discord.Color.green()),
            "mittel": (1, 50, 51, 100, discord.Color.yellow()),
            "schwer": (1, 100, 101, 200, discord.Color.red()),
        }
        difficulty = random.choice(list(difficulties.keys()))
        (least_min, highest_min, least_max, highest_max, color) = difficulties[difficulty]

        self.id = int(time.time() * 1000)
        self.number1 = random.randint(least_min, highest_min)
        self.number2 = random.randint(least_max, highest_max)
        self.number = random.randint(self.number1, self.number2)

        embed = discord.Embed(
            title="Guess the Number",
            description=f"Die Zahl die zu erraten ist befindet sich **zwischen {self.number1} und {self.number2}**.\n "
            f"Die Schwierigkeit ist **{difficulty}**.",
            color=color,
            timestamp=datetime.now(tz=self.de),
        )
        self.last_game_message = await utils.safe_embed_channel_send(self.bot, self.channel, embed=embed)
        self.race_condition = False

        await utils.safe_pin(self.last_game_message, "GTN GAME")

        self.last_game_message = self.last_game_message.id

        await dbhandler.db.new_gtn_game(self.id, self.number1, self.number2, self.number, self.last_game_message)

        async for message in self.bot.get_channel(self.channel).history(limit=1):
            if message.type == discord.MessageType.pins_add:
                await utils.safe_delete(message)

        log.info(f"Guess Number was sent, the number is {self.number}.")

    @commands.Cog.listener()
    async def on_ready(self):
        last_game_row = await dbhandler.db.get_latest_row("gtn_save", "id")

        if last_game_row is None or last_game_row[5] == 1:
            await self.new_game()
            log.debug("gtn started new game")
        else:
            self.id = last_game_row[0]
            self.number1 = last_game_row[1]
            self.number2 = last_game_row[2]
            self.number = last_game_row[3]
            self.last_game_message = last_game_row[4]
            log.debug(f"gtn restored last game with the number {self.number}")
        log.info("guess_number.py is ready")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.race_condition is True or message.channel.id != self.channel or message.author.bot:
            return

        try:
            guess = int(message.content)
        except ValueError:
            return

        await dbhandler.db.add_smth_and_insert("gtn_stats", "user_id", message.author.id, "guess", 1)

        if guess == self.number:
            self.race_condition = True
            await dbhandler.db.add_smth("gtn_stats", "wins", 1, "user_id", message.author.id)

            result = await dbhandler.db.get_one_row("gtn_stats", "user_id", message.author.id)
            wins = result[1]
            guesses = result[2]
            winrate = round((wins / guesses) * 100 if guesses > 0 else 0)

            embed = discord.Embed(
                title="RICHTIG!",
                description=f"{message.author.mention} hat die Zahl **{self.number}** erraten.",
                color=discord.Color.green(),
            )
            embed.set_footer(text=f"Du hast eine Gewinnchance von {round(winrate, 2)}%.")
            await utils.safe_embed_channel_send(self.bot, self.channel, embed=embed)
            await dbhandler.db.set_smth("gtn_save", "done", 1, "id", self.id)

            if self.last_game_message:
                await utils.safe_unpin(self.last_game_message, message.channel)

            await message.add_reaction("✅")
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
