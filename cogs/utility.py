import urllib.parse

import discord
from discord import Option, slash_command
from ezcord import log
from ezcord.internal.dc import commands


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("utility.py is ready")

    @slash_command()
    async def avatar(self, ctx, user: Option(discord.Member, required=False)):
        log.debug(f"{ctx.author.name} used /avatar")

        if not user:
            user = ctx.author

        avatar_url = user.display_avatar.replace(size=4096).url
        embed = discord.Embed(title=f"Avatar von {user.display_name}", color=discord.Color.random())
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"User ID: {user.id}")

        button = discord.ui.Button(label="Download Avatar", url=avatar_url)
        view = discord.ui.View()
        view.add_item(button)

        await ctx.respond(embed=embed, view=view)

    @slash_command()
    async def mc_skin(
        self,
        ctx,
        username: Option(str, "Minecraft Benutzername"),
        render: Option(
            str,
            "Wähle die Pose",
            required=False,
            choices=[
                "default",
                "marching",
                "walking",
                "crouching",
                "crossed",
                "criss_cross",
                "ultimate",
                "isometric",
                "cheering",
                "relaxing",
                "trudging",
                "cowering",
                "pointing",
                "lunging",
                "dungeons",
                "facepalm",
                "sleeping",
                "dead",
                "archer",
                "kicking",
                "mojavatar",
                "reading",
                "bitzel",
                "pixel",
            ],
            default="default",
        ),
    ):
        log.debug(f"{ctx.author.name} used /mc_skin")
        await ctx.defer()

        if username != urllib.parse.quote(username):
            await ctx.respond("Der eingegebene Username ist nicht valide.", ephemeral=True)
            return

        render_url = f"https://starlightskins.lunareclipse.studio/render/{render}/{username}/full"

        embed = discord.Embed(title=f"Skin von {username}", color=discord.Color.random())
        embed.set_image(url=render_url)
        embed.set_thumbnail(url=f"https://starlightskins.lunareclipse.studio/render/head/{username}/full")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Download", url=f"https://minotar.net/download/{username}"))
        view.add_item(discord.ui.Button(label="Download Render", url=render_url))

        await ctx.respond(embed=embed, view=view)


def setup(bot):
    bot.add_cog(Utility(bot))
