from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import discord

# Hilfsfunktionen


def _is_locked(channel: discord.VoiceChannel) -> bool:
    """Gibt True zurück wenn @everyone connect=False hat."""
    perms = channel.overwrites_for(channel.guild.default_role)
    return perms.connect is False


def _build_member_options(
    channel: discord.VoiceChannel,
    exclude_id: int | None = None,
) -> tuple[list[discord.SelectOption], bool]:

    members = [m for m in channel.members if not m.bot]
    if exclude_id:
        members = [m for m in members if m.id != exclude_id]

    if not members:
        return (
            [
                discord.SelectOption(
                    label="Keine weiteren Mitglieder",
                    value="none",
                    emoji="😴",
                    description="Aktuell ist niemand anderes im Channel",
                )
            ],
            False,
        )

    return (
        [
            discord.SelectOption(
                label=m.display_name[:100],
                value=str(m.id),
                emoji="👤",
            )
            for m in members
        ],
        True,
    )


# Main Panel Builder


def build_control_panel(
    channel: discord.VoiceChannel,
    owner: discord.Member,
) -> list:
    """
    Erstellt das Control Panel.
    """
    cid = channel.id
    locked = _is_locked(channel)
    member_count = len([m for m in channel.members if not m.bot])
    limit_str = "∞" if channel.user_limit == 0 else str(channel.user_limit)
    opts, has_members = _build_member_options(channel, exclude_id=owner.id)

    # Header
    header = discord.ui.TextDisplay(
        content=(
            f"## VoiceChat Controll Panel\n"
            f"**{discord.utils.escape_markdown(channel.name)}**\n"
            f"👑 Owner: {owner.mention}\n"
            f"👥 {member_count}/{limit_str} Mitglieder\n"
            f"{'🔒 Gesperrt' if locked else '🔓 Offen'}"
        )
    )

    # Settings
    settings_label = discord.ui.TextDisplay(content="### Channel Einstellungen")
    settings_row = discord.ui.ActionRow(
        discord.ui.Button(
            label="🔓 Entsperren" if locked else "🔒 Sperren",
            style=discord.ButtonStyle.success if locked else discord.ButtonStyle.secondary,
            custom_id=f"tv_lock_{cid}",
        ),
        discord.ui.Button(
            label="✏️ Umbenennen",
            style=discord.ButtonStyle.primary,
            custom_id=f"tv_rename_{cid}",
        ),
        discord.ui.Button(
            label="👥 Benutzerlimit",
            style=discord.ButtonStyle.primary,
            custom_id=f"tv_limit_{cid}",
        ),
        discord.ui.Button(
            label="🗑️ Channel löschen",
            style=discord.ButtonStyle.danger,
            custom_id=f"tv_delete_{cid}",
        ),
    )

    # Member Settings
    members_label = discord.ui.TextDisplay(content="### User Verwaltung")
    kick_row = discord.ui.ActionRow(
        discord.ui.Select(
            placeholder="🚪  User aus dem Channel kicken …",
            custom_id=f"tv_kick_{cid}",
            options=opts,
            disabled=not has_members,
        ),
    )
    ban_row = discord.ui.ActionRow(
        discord.ui.Select(
            placeholder="🚫  User dauerhaft bannen …",
            custom_id=f"tv_ban_{cid}",
            options=opts,
            disabled=not has_members,
        ),
    )
    transfer_row = discord.ui.ActionRow(
        discord.ui.Select(
            placeholder="👑  Ownership übertragen …",
            custom_id=f"tv_transfer_{cid}",
            options=opts,
            disabled=not has_members,
        ),
    )

    # Voice Settings
    voice_label = discord.ui.TextDisplay(content="### Voice Aktionen")
    voice_row = discord.ui.ActionRow(
        discord.ui.Button(
            label="🔇 Alle muten",
            style=discord.ButtonStyle.secondary,
            custom_id=f"tv_muteall_{cid}",
        ),
        discord.ui.Button(
            label="🔊 Alle unmuten",
            style=discord.ButtonStyle.secondary,
            custom_id=f"tv_unmuteall_{cid}",
        ),
        discord.ui.Button(
            label="📋 Bans verwalten",
            style=discord.ButtonStyle.secondary,
            custom_id=f"tv_bans_{cid}",
        ),
        discord.ui.Button(
            label="🔑 Whitelist",
            style=discord.ButtonStyle.secondary,
            custom_id=f"tv_whitelist_{cid}",
        ),
    )

    footer = discord.ui.TextDisplay(content="-# Nur der Talk Owner kann einstellungen verändern.")

    return [
        discord.ui.Container(
            header,
            settings_label,
            settings_row,
            members_label,
            kick_row,
            ban_row,
            transfer_row,
            voice_label,
            voice_row,
            footer,
            color=discord.Color.blurple(),
        )
    ]


# Modals
UpdateCallback = Callable[[discord.VoiceChannel], Coroutine[Any, Any, None]]


class RenameModal(discord.ui.Modal):
    """Modal zum Umbenennen."""

    def __init__(self, channel: discord.VoiceChannel, update_cb: UpdateCallback):
        super().__init__(title="✏️ Channel umbenennen")
        self.channel = channel
        self.update_cb = update_cb
        self.add_item(
            discord.ui.InputText(
                label="Neuer Channel-Name",
                placeholder=channel.name,
                max_length=100,
                style=discord.InputTextStyle.short,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        new_name = self.children[0].value.strip()
        if not new_name:
            await interaction.response.send_message("Name darf nicht leer sein.", ephemeral=True)
            return
        await self.channel.edit(
            name=new_name,
            reason=f"Umbenannt von {interaction.user.display_name}",
        )
        await interaction.response.send_message(
            f"Channel wurde in `{discord.utils.escape_markdown(new_name)}` umbenannt.",
            ephemeral=True,
        )
        await self.update_cb(self.channel)


class LimitModal(discord.ui.Modal):
    """Modal zum Setzen des Userlimits."""

    def __init__(self, channel: discord.VoiceChannel, update_cb: UpdateCallback):
        super().__init__(title="👥 Benutzerlimit setzen")
        self.channel = channel
        self.update_cb = update_cb
        self.add_item(
            discord.ui.InputText(
                label="Benutzerlimit (0 = kein Limit, max. 99)",
                placeholder=str(channel.user_limit),
                max_length=2,
                style=discord.InputTextStyle.short,
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            limit = int(self.children[0].value.strip())
            if not 0 <= limit <= 99:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Bitte gib eine Zahl zwischen **0** und **99** ein.", ephemeral=True
            )
            return
        await self.channel.edit(
            user_limit=limit,
            reason=f"Limit geändert von {interaction.user.display_name}",
        )
        limit_str = "kein Limit" if limit == 0 else f"**{limit} User**"
        await interaction.response.send_message(f"Benutzerlimit auf {limit_str} gesetzt!", ephemeral=True)
        await self.update_cb(self.channel)


# Sub-Views


class UnbanView(discord.ui.View):
    """
    Ephemerer View zur Ban Verwaltung.
    """

    def __init__(
        self,
        channel: discord.VoiceChannel,
        ban_rows: list[dict],
        db,
        update_cb: UpdateCallback,
    ):
        super().__init__(timeout=120)
        self.channel = channel
        self.db = db
        self.update_cb = update_cb

        options = []
        for row in ban_rows:
            uid = row[1]
            member = channel.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            options.append(
                discord.SelectOption(
                    label=name[:100],
                    value=str(uid),
                    emoji="🚫",
                )
            )

        select = discord.ui.Select(
            placeholder="🚫  User entbannen …",
            options=options,
            min_values=1,
            max_values=min(len(options), 5),
        )
        select.callback = self._unban_callback
        self.add_item(select)

    async def _unban_callback(self, interaction: discord.Interaction) -> None:
        names = []
        for uid_str in interaction.data["values"]:
            uid = int(uid_str)
            target = interaction.guild.get_member(uid)
            if target:
                await self.channel.set_permissions(target, overwrite=None)
                names.append(target.display_name)
            else:
                names.append(f"User {uid}")
            await self.db.remove_ban(self.channel.id, uid)

        joined = ", ".join(f"**{n}**" for n in names)
        suffix = "n" if len(names) > 1 else ""
        await interaction.response.edit_message(
            content=f"{joined} wurde{suffix} erfolgreich entbannt!",
            view=None,
        )
        await self.update_cb(self.channel)


class WhitelistView(discord.ui.View):
    """
    Ephemerer View zur Whitelist-Verwaltung (wenn Channel gesperrt ist).
    Ermöglicht das Hinzufügen/Entfernen von Usern mit connect=True.
    """

    def __init__(
        self,
        channel: discord.VoiceChannel,
        whitelisted: list[int],
        db,
        update_cb: UpdateCallback,
    ):
        super().__init__(timeout=120)
        self.channel = channel
        self.db = db
        self.update_cb = update_cb

        guild_members = [m for m in channel.guild.members if not m.bot and m.id not in whitelisted][:25]

        if guild_members:
            add_opts = [
                discord.SelectOption(
                    label=m.display_name[:100],
                    value=f"add_{m.id}",
                    emoji="✅",
                )
                for m in guild_members
            ]
            add_select = discord.ui.Select(
                placeholder="User zur Whitelist hinzufügen…",
                options=add_opts,
                min_values=1,
                max_values=min(len(add_opts), 5),
            )
            add_select.callback = self._add_callback
            self.add_item(add_select)

        if whitelisted:
            rm_opts = []
            for uid in whitelisted:
                m = channel.guild.get_member(uid)
                name = m.display_name if m else f"User {uid}"
                rm_opts.append(
                    discord.SelectOption(
                        label=name[:100],
                        value=f"rm_{uid}",
                        emoji="❌",
                    )
                )
            rm_select = discord.ui.Select(
                placeholder="❌  User von Whitelist entfernen …",
                options=rm_opts[:25],
                min_values=1,
                max_values=min(len(rm_opts), 5),
            )
            rm_select.callback = self._remove_callback
            self.add_item(rm_select)

    async def _add_callback(self, interaction: discord.Interaction) -> None:
        added = []
        for val in interaction.data["values"]:
            uid = int(val.replace("add_", ""))
            target = interaction.guild.get_member(uid)
            if target:
                await self.channel.set_permissions(target, connect=True)
                await self.db.add_whitelist(self.channel.id, uid)
                added.append(target.display_name)
        joined = ", ".join(f"**{n}**" for n in added)
        await interaction.response.send_message(
            f"{joined} wurde{'n' if len(added) > 1 else ''} zur Whitelist hinzugefügt!",
            ephemeral=True,
        )
        await self.update_cb(self.channel)

    async def _remove_callback(self, interaction: discord.Interaction) -> None:
        removed = []
        for val in interaction.data["values"]:
            uid = int(val.replace("rm_", ""))
            target = interaction.guild.get_member(uid)
            if target:
                await self.channel.set_permissions(target, overwrite=None)
                removed.append(target.display_name)
            await self.db.remove_whitelist(self.channel.id, uid)
        joined = ", ".join(f"**{n}**" for n in removed)
        await interaction.response.send_message(
            f"{joined} wurde{'n' if len(removed) > 1 else ''} von der Whitelist entfernt!",
            ephemeral=True,
        )
        await self.update_cb(self.channel)
