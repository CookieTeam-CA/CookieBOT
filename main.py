import os

import yaml
from dotenv import load_dotenv

from bot.core.bot import MyBot

if __name__ == "__main__":
    load_dotenv()

    bot = MyBot()

    with open("data/commands.yml", encoding="utf-8") as f:
        cmd_locales = yaml.safe_load(f)

    bot.load_extension("bot.cogs.counting")
    bot.load_extension("bot.cogs.flagguess")
    bot.load_extension("bot.cogs.guess_number")
    # bot.load_extension("bot.cogs.memes")
    bot.load_extension("bot.cogs.one_word")
    bot.load_extension("bot.cogs.temp_voice")
    bot.load_extension("bot.cogs.utility")
    bot.load_extension("bot.cogs.reactionrole")

    bot.localize_commands(cmd_locales)
    bot.run(os.getenv("TOKEN"))
