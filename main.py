import configparser
import logging
import os
import shutil
import sys
from logging.handlers import RotatingFileHandler

import discord
import ezcord
from dotenv import load_dotenv
from ezcord import log

from utils import greeter_builder


os.makedirs("logs", exist_ok=True)

file_handler = RotatingFileHandler(
    filename="logs/bot.log", maxBytes=2 * 1024 * 1024, backupCount=10, encoding="utf-8"
)

file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
)

logger = ezcord.logs.set_log(
    log_level=logging.DEBUG,
    console=True,
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger.addHandler(file_handler)


bot = ezcord.Bot(
    intents=discord.Intents.all(), debug_guilds=None, ready_event=None, language="de"
)
bot.add_help_command()

CONFIG_PATH = "config.cfg"
if not os.path.exists(CONFIG_PATH):
    shutil.copy2("template/config-template.cfg", CONFIG_PATH)
    log.critical("I created the config.cfg file. Please configure all IDs in it.")
    sys.exit("The program terminated because the configuration didn't exist.")

parser = configparser.ConfigParser()
parser.read(CONFIG_PATH)

guild_id = int(parser["GENERAL"]["guild_id"])
log_channel = int(parser["CHANNELS"]["log_channel"])
im_log_channel = int(parser["CHANNELS"]["im_log_channel"])
welcome_channel = int(parser["CHANNELS"]["welcome_channel"])
member_role = int(parser["WELCOME"]["member_role"])


@bot.event
async def on_ready():
    print("System is up and running.")


@bot.event
async def on_member_join(member):
    log.info(f"{member} joined {member.guild.name}")
    if guild_id == member.guild.id:
        if member.bot:
            embed = greeter_builder(
                title="Discord Bot hinzugefügt",
                description=f"Der Bot {member.mention} wurde hinzugefügt.",
                color=discord.Color.green(),
                member=member,
            )
            await bot.get_channel(im_log_channel).send(embed=embed)
            return

        file = discord.File("img/join.gif", filename="join.gif")

        embed = greeter_builder(
            title=":wave: Hallo! Cool, dass du hierhergefunden hast!",
            description=f"Hallo {member.mention}, wir hoffen, dass du viel Spaß auf diesem Server haben wirst.",
            color=discord.Color.orange(),
            member=member,
            image="join",
        )
        await bot.get_channel(welcome_channel).send(embed=embed, file=file)
        role = discord.utils.get(member.guild.roles, id=member_role)
        await member.add_roles(role)
    else:
        log.warning(f"{member} joined a Server that wasn't configured")


@bot.event
async def on_member_remove(member):
    log.info(f"{member} left from {member.guild.name}")
    if guild_id == member.guild.id:
        if member.bot:
            embed = greeter_builder(
                title="Discord Bot entfernt",
                description=f"Der Bot {member.mention} wurde entfernt.",
                color=discord.Color.red(),
                member=member,
            )
            await bot.get_channel(im_log_channel).send(embed=embed)
            return
        file = discord.File("img/leave.gif", filename="leave.gif")

        embed = greeter_builder(
            title=":wave: Tschüss! Er war noch viel zu jung, um zu sterben.",
            description=f"Tschüss, {member.mention}! Hoffentlich kommst du bald zurück!",
            color=discord.Color.red(),
            member=member,
            image="leave",
        )
        await bot.get_channel(welcome_channel).send(embed=embed, file=file)
    else:
        log.warning(f"{member} left from a Server that wasn't configured")


if __name__ == "__main__":
    load_dotenv()
    bot.load_extension("cogs.guess_number")
    bot.load_extension("cogs.one_word")
    # bot.load_extension("cogs.memes")
    # bot.load_extension("cogs.games")
    bot.run(os.getenv("TOKEN"))
