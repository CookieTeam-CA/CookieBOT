import discord
from discord import Role
from discord.ext import commands
from ezcord import log
from ezcord.internal.dc import slash_command

from bot.db import handler
from bot.utils.helpers import load_config
from bot.utils.pagination import EmbedPaginator, build_pages


class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = load_config("GENERAL", "guild_id", "int")

    def error_embed(self, error):
        return discord.Embed(
            title="Message ID oder Emoji ungültig.", description=f"Error: ```{error}```", color=discord.Color.red()
        )

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("reactionrole.py is ready")

    @slash_command()
    @commands.has_permissions(administrator=True)
    async def add_reactionrole(self, ctx, message_id: str, emoji: str, role: Role):
        try:
            msg_id = int(message_id)
        except ValueError:
            return await ctx.respond(embed=self.error_embed("Ungültige Message ID."), ephemeral=True)

        exists = await handler.db.get_specific_reactionrole(msg_id, emoji)
        if exists:
            return await ctx.respond(
                "Reactionrole auf dieser Nachricht mit diesem Emoji existiert bereits.",
                ephemeral=True,
            )
        try:
            message = await ctx.channel.fetch_message(msg_id)
            await message.add_reaction(emoji)
        except Exception as e:
            return await ctx.respond(embed=self.error_embed(e), ephemeral=True)

        await handler.db.create_rr(msg_id, emoji, role.id)
        await ctx.respond(
            f"Reactionrole erstellt mit dem Emoji {emoji} der Role {role.mention} auf der Nachricht `{msg_id}`",
            ephemeral=True,
        )

    @slash_command()
    @commands.has_permissions(administrator=True)
    async def remove_reactionrole(self, ctx, message_id: str, emoji: str):
        try:
            msg_id = int(message_id)
        except ValueError:
            return await ctx.respond(embed=self.error_embed("Ungültige Message ID."), ephemeral=True)

        try:
            message = await ctx.channel.fetch_message(msg_id)
            await handler.db.delete_rr(msg_id, emoji)
            await message.remove_reaction(emoji, self.bot.user)
        except Exception as e:
            return await ctx.respond(embed=self.error_embed(e), ephemeral=True)

        await ctx.respond(
            f"Reactionrole von der Nachricht `{msg_id}` mit dem Emoji {emoji} gelöscht.",
            ephemeral=True,
        )

    @slash_command()
    @commands.has_permissions(administrator=True)
    async def list_reactionroles(self, ctx):
        data = await handler.db.get_reactionroles()

        if not data:
            return await ctx.respond("Keine Reaction Roles vorhanden.", ephemeral=True)

        def builder(i, chunk, embed):
            for row in chunk:
                msg_id, emoji, role_id = row
                embed.add_field(
                    name=f"{emoji} — Message `{msg_id}`",
                    value=f"Rolle: <@&{role_id}>",
                    inline=False,
                )

        pages = build_pages(data, title="⚡ Reaction Roles", builder=builder)
        await EmbedPaginator(pages).send(ctx, ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        try:
            row = await handler.db.get_specific_reactionrole(payload.message_id, payload.emoji.name)
        except Exception:
            return
        if not row:
            return

        guild = self.bot.get_guild(self.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(row[2])  # row[2] = role_id
        if member and role:
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        try:
            row = await handler.db.get_specific_reactionrole(payload.message_id, payload.emoji.name)
        except Exception:
            return
        if not row:
            return

        guild = self.bot.get_guild(self.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(row[2])  # row[2] = role_id
        if member and role:
            await member.remove_roles(role)


def setup(bot):
    bot.add_cog(ReactionRole(bot))
