import difflib
from datetime import datetime
from zoneinfo import ZoneInfo

from discord import Color, DMChannel, Embed
from discord.ext import commands
from ezcord import log

from bot.utils.helpers import load_config

de = ZoneInfo("Europe/Berlin")


class ModerationLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logchannel = load_config("CHANNELS", "log_channel", "int")

    async def send_embed(self, embed, user):
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url, url=user.jump_url)
        channel = self.bot.get_channel(self.logchannel)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("moderation_log.py is ready")

    @commands.Cog.listener()
    async def on_application_command(self, context):
        log.info(f"{context.author} used /{context.command} in {context.channel}")
        embed = Embed(
            description=f"{context.author.mention} used /{context.command} in {context.channel.jump_url}",
            color=Color.blue(),
            timestamp=datetime.now(tz=de),
        )
        await self.send_embed(embed, context.author)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        embed = Embed(
            description=f"{message.author.mention} deleted a message in {message.channel.jump_url}",
            color=Color.red(),
            timestamp=datetime.now(tz=de),
        )
        embed.add_field(name="Message content:", value=message.content, inline=False)
        embed.add_field(name="Message send date:", value=message.created_at, inline=False)
        await self.send_embed(embed, message.author)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
        if before.content == after.content:
            return

        before_words = before.content.split()
        after_words = after.content.split()

        diff = difflib.ndiff(before_words, after_words)

        added = []
        removed = []
        for token in diff:
            if token.startswith("+ "):
                added.append(f"**{token[2:]}**")
            elif token.startswith("- "):
                removed.append(f"~~{token[2:]}~~")

        changes = []
        if removed:
            changes.append("Entfernt: " + " ".join(removed))
        if added:
            changes.append("Hinzugefügt: " + " ".join(added))

        diff_value = "\n".join(changes) or "Keine Textänderungen"

        embed = Embed(
            description=f"{before.author.mention} edited this message: {after.jump_url}",
            color=Color.blue(),
            timestamp=datetime.now(tz=de),
        )
        embed.add_field(name="Before:", value=before.content, inline=False)
        embed.add_field(name="After:", value=after.content, inline=False)
        embed.add_field(name="Changes:", value=diff_value, inline=False)
        await self.send_embed(embed, before.author)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or message.author.bot:
            return

        if isinstance(message.channel, DMChannel):
            log.info(f"{message.author} sent the bot a private message")
            embed = Embed(
                description=f"{message.author.mention} has sent the bot a private message", color=Color.blue()
            )
            embed.add_field(name="Content:", value=message.content, inline=False)
            await self.send_embed(embed, message.author)


def setup(bot):
    bot.add_cog(ModerationLog(bot))
