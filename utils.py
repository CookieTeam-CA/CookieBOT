import discord
from datetime import datetime
from zoneinfo import ZoneInfo

de = ZoneInfo('Europe/Berlin')

def greeter_builder(title, description, color, member, image: str | None = None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(tz=de),
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    if image:
        embed.set_image(url=f"attachment://{image}.gif")
    return embed