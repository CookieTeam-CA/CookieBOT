import configparser
import json
import random
import asyncio

from ezcord import log
from ezcord.internal.dc import commands
from utils import safe_delete


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class Wordle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parser = configparser.ConfigParser()
        self.parser.read("config.cfg")
        try:
            self.channel = int(self.parser["CHANNELS"]["wordle"])
        except (KeyError, ValueError):
            log.error("Wordle ID not found in config.cfg!")
            self.channel = None

        self.wordle_guess_words = load_json("data/wordle_guess_words.json")
        self.wordle_word = None
        self.guesses = []

    async def start_wordle(self):
        self.guesses = []

        data = load_json("data/wordle_words.json")
        self.wordle_word = random.choice(data["data"])

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("wordle.py is ready")

        # restore last game

        if self.wordle_word is None:
            await self.start_wordle()

        log.debug(self.wordle_word)

    @commands.Cog.listener()
    async def on_message(self, message):
        content = message.content

        if message.channel.id != self.channel or message.author.bot or len(content) != 5:
            return
        if len(content.split()) == 1:
            self.guesses.append((content, message.author.id))

            if content.lower() == self.wordle_word:
                await message.reply(
                    f"Glückwunsch! Du hast das Wort **{self.wordle_word}** erraten! Es wurden {len(self.guesses)} Versuche benötigt.",
                    mention_author=False,
                )
                await self.start_wordle()

            if len(self.guesses) == 6:
                await message.reply(
                    f"Das Wort war **{self.wordle_word}**. Alle 6 Versuche wurden verbraucht!", mention_author=False
                )

            if content.lower() != self.wordle_word:
                if content.lower() not in self.wordle_guess_words:
                    msg = await message.reply("Dieses Wort ist nicht in der Wortliste.", mention_author=False)
                    await safe_delete(message)
                    await asyncio.sleep(5)
                    await safe_delete(msg)
                    return
                feedback = ""
                for i in range(5):
                    if content[i].lower() == self.wordle_word[i]:
                        feedback += "🟩"
                    elif content[i].lower() in self.wordle_word:
                        feedback += "🟨"
                    else:
                        feedback += "⬛"
                await message.reply(feedback, mention_author=False)
        else:
            msg = await message.reply("Du darfst nur ein Wort schreiben.", mention_author=False)
            await safe_delete(message)
            await asyncio.sleep(5)
            await safe_delete(msg)


def setup(bot):
    bot.add_cog(Wordle(bot))
