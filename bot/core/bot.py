import configparser
import logging
import os
import shutil
import sys
from logging.handlers import RotatingFileHandler

import discord
import ezcord
from ezcord import log

from bot.db import handler
from bot.utils.helpers import greeter_builder, safe_add_role, safe_embed_channel_send

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

if not os.path.exists(".env"):
    with open(".env", "w", encoding="utf-8") as f:
        f.write("TOKEN=\n")

file_handler = RotatingFileHandler(filename="logs/bot.log", maxBytes=2 * 1024 * 1024, backupCount=10, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"))

logger = ezcord.logs.set_log(
    log_level=logging.DEBUG,
    console=True,
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
)
logger.addHandler(file_handler)


class MyBot(ezcord.Bot):
    def __init__(self):
        super().__init__(
            intents=discord.Intents.all(),
            debug_guilds=None,
            ready_event=None,
            language="de",
        )
        self.add_help_command()
        self._load_config()

    def _load_config(self):
        config_path = "config/config.cfg"
        if not os.path.exists(config_path):
            shutil.copy2("config/config-template.cfg", config_path)
            log.critical("I created the config.cfg file. Please configure all IDs in it.")
            sys.exit("The program terminated because the configuration didn't exist.")

        parser = configparser.ConfigParser()
        parser.read(config_path)

        try:
            self.guild_id = int(parser["GENERAL"]["guild_id"])
            self.log_channel = int(parser["CHANNELS"]["log_channel"])
            self.im_log_channel = int(parser["CHANNELS"]["im_log_channel"])
            self.welcome_channel = int(parser["CHANNELS"]["welcome_channel"])
            self.member_role = int(parser["WELCOME"]["member_role"])
            self.flag_guess_channel = int(parser["CHANNELS"]["flags"])
        except (KeyError, ValueError) as e:
            log.critical(f"Error reading config.cfg: {e}. Check if all IDs are integers.")
            sys.exit(1)

    async def on_ready(self):
        await handler.db.setup()
        print("System is up and running.")

    async def on_member_join(self, member: discord.Member):
        log.info(f"{member} joined {member.guild.name}")
        if self.guild_id != member.guild.id:
            log.warning(f"{member} joined a Server that wasn't configured")
            return

        if member.bot:
            embed = greeter_builder(
                title="Discord Bot hinzugefügt",
                description=f"Der Bot {member.mention} wurde hinzugefügt.",
                color=discord.Color.green(),
                member=member,
            )
            await safe_embed_channel_send(self, self.im_log_channel, embed)
            return

        gif_path = "assets/join.gif"
        file, image_payload = None, None
        if os.path.exists(gif_path):
            file = discord.File(gif_path, filename="join.gif")
            image_payload = "join"
        else:
            log.warning(f"File {gif_path} missing. Sending without image.")

        embed = greeter_builder(
            title=":wave: Hallo! Cool, dass du hierhergefunden hast!",
            description=f"Hallo {member.mention}, wir hoffen, dass du viel Spaß auf diesem Server haben wirst.",
            color=discord.Color.orange(),
            member=member,
            image=image_payload,
        )
        await safe_embed_channel_send(self, self.welcome_channel, embed, file)
        await safe_add_role(member, self.member_role)

    async def on_member_remove(self, member: discord.Member):
        log.info(f"{member} left from {member.guild.name}")
        if self.guild_id != member.guild.id:
            log.warning(f"{member} left from a Server that wasn't configured")
            return

        if member.bot:
            embed = greeter_builder(
                title="Discord Bot entfernt",
                description=f"Der Bot {member.mention} wurde entfernt.",
                color=discord.Color.red(),
                member=member,
            )
            await safe_embed_channel_send(self, self.im_log_channel, embed)
            return

        gif_path = "assets/leave.gif"
        file, image_payload = None, None
        if os.path.exists(gif_path):
            file = discord.File(gif_path, filename="leave.gif")
            image_payload = "leave"
        else:
            log.warning(f"File {gif_path} missing. Sending without image.")

        embed = greeter_builder(
            title=":wave: Tschüss! Er war noch viel zu jung, um zu sterben.",
            description=f"Tschüss, {member.mention}! Hoffentlich kommst du bald zurück!",
            color=discord.Color.red(),
            member=member,
            image=image_payload,
        )
        await safe_embed_channel_send(self, self.welcome_channel, embed, file)
