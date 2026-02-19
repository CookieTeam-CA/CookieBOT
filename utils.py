from contextlib import suppress
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from ezcord import log

de = ZoneInfo("Europe/Berlin")


def greeter_builder(title, description, color, member, image: str | None = None):
    """Function to build greeter message"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(tz=de),
    )
    avatar_url = member.display_avatar.url if member.display_avatar else member.default_avatar.url
    embed.set_thumbnail(url=avatar_url)

    if image:
        embed.set_image(url=f"attachment://{image}.gif")
    return embed


async def safe_add_role(member, role_id):
    """Function to add a role to a member with Error Handler"""
    role = member.guild.get_role(role_id)

    if role:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            log.error(f"Permissions missing to add role {role.name}")
        except discord.HTTPException as e:
            log.error(f"Error adding role: {e}")
    else:
        log.error(f"Role ID {role} not found on server!")


async def safe_embed_channel_send(bot, channel, embed=None, file=None):
    """Function to send embed to channel with error handler"""
    channel = bot.get_channel(channel)

    if channel:
        try:
            return await channel.send(embed=embed, file=file)
        except discord.HTTPException as e:
            log.error(f"Failed to send message to {channel.name}: {e}")
    else:
        log.error(f"Channel ID {channel} not found.")
    return None


async def safe_delete(message):
    """Function to delete a message with error handler if the message doesn't exist for example"""
    with suppress(discord.HTTPException, discord.NotFound, discord.Forbidden):
        await message.delete()

async def safe_unpin(message_id, channel):
    """Function to unpin a message with error handler if the message doesn't exist for example"""
    if not message_id or not channel:
        return
    with suppress(discord.HTTPException, discord.NotFound):
        msg = await channel.fetch_message(message_id)
        await msg.unpin()
