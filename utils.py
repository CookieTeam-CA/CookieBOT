from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from ezcord import log

de = ZoneInfo("Europe/Berlin")


def greeter_builder(title, description, color, member, image: str | None = None):
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
    channel = bot.get_channel(channel)

    if channel:
        try:
            await channel.send(embed=embed, file=file)
        except discord.HTTPException as e:
            log.error(f"Failed to send message to {channel.name}: {e}")
    else:
        log.error(f"Channel ID {channel} not found.")
