import urllib.parse

import discord
from discord import Option, slash_command
from ezcord import log
from ezcord.internal.dc import commands

from bot.db.handler import db


class SettingButtons(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        self.scse = discord.Embed(
            title="Erfolgreich geändert!",
            description="Die Einstellung wurde erfolgreich geändert",
            color=discord.Color.green(),
        )
        self.suse = discord.Embed(
            title="Nichts verändert.",
            description="Die Einstellung wurde nicht verändert da sie bereits so eingestellt ist.",
            color=discord.Color.light_gray(),
        )

    @discord.ui.button(label="Pings An", style=discord.ButtonStyle.green, row=0)
    async def button_callback0(self, button, interaction):
        embed = self.scse if await db.change_setting(interaction.user.id, "ping", 1) == 1 else self.suse

        await interaction.respond(embed=embed, ephemeral=True)

    @discord.ui.button(label="Pings Aus", style=discord.ButtonStyle.red, row=0)
    async def button_callback1(self, button, interaction):
        embed = self.scse if await db.change_setting(interaction.user.id, "ping", 0) == 1 else self.suse

        await interaction.respond(embed=embed, ephemeral=True)

    @discord.ui.button(label="Direkt Nachrichten An", style=discord.ButtonStyle.green, row=1)
    async def button_callback2(self, button, interaction):
        embed = self.scse if await db.change_setting(interaction.user.id, "dm", 1) == 1 else self.suse

        await interaction.respond(embed=embed, ephemeral=True)

    @discord.ui.button(label="Direkt Nachrichten Aus", style=discord.ButtonStyle.red, row=1)
    async def button_callback3(self, button, interaction):
        embed = self.scse if await db.change_setting(interaction.user.id, "dm", 0) == 1 else self.suse

        await interaction.respond(embed=embed, ephemeral=True)


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("utility.py is ready")

    @slash_command()
    async def avatar(self, ctx, user: Option(discord.Member, required=False)):  # type: ignore
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
        username: Option(str, "Minecraft Benutzername"),  # type: ignore
        render: Option(  # type: ignore
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

    @slash_command()
    async def settings(self, ctx):  # type: ignore
        embed = discord.Embed(
            title="Einstellungen",
            description="Hier kannst eigene Einstellungen im bezug zum Bot treffen.",
            color=discord.Color.blurple(),
        )
        await ctx.respond(embed=embed, view=SettingButtons(self))


def setup(bot):
    bot.add_cog(Utility(bot))
