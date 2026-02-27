from __future__ import annotations

import configparser
import random
from contextlib import suppress

import discord
from ezcord import log
from ezcord.internal.dc import commands

import dbhandler
from temp_voice_ui import (
    LimitModal,
    RenameModal,
    UnbanView,
    WhitelistView,
    build_control_panel,
)

OWNER_OVERWRITE = discord.PermissionOverwrite(
    manage_channels=True,
    manage_permissions=True,
    move_members=True,
    mute_members=True,
    deafen_members=True,
    connect=True,
    speak=True,
    priority_speaker=True,
    stream=True,
)


class TempVoice(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

        parser = configparser.ConfigParser()
        parser.read("config.cfg")
        try:
            self.create_channel_id: int = int(parser["TEMP_VOICE"]["create_channel"])
            self.category_id: int = int(parser["TEMP_VOICE"]["category"])
        except (KeyError, ValueError):
            log.error("Config-Keys fehlen: create_channel / category")
            self.create_channel_id = 0
            self.category_id = 0

        self._temp_channels: dict[int, discord.VoiceChannel] = {}
        self._channel_owners: dict[int, int] = {}
        self._panel_messages: dict[int, discord.Message] = {}

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info("Loading stored channels...")
        await self._restore_state()
        log.info("tempvoice.py is ready")

    async def _restore_state(self) -> None:
        rows = await dbhandler.db.get_all_temp_channels()
        if not rows:
            return

        for row in rows:
            # Tuple: (channel_id=0, owner_id=1, panel_msg_id=2, created_at=3)
            cid = row[0]
            channel = self.bot.get_channel(cid)

            if not channel:
                await dbhandler.db.delete_temp_channel(cid)
                continue

            owner_id = row[1]
            self._temp_channels[cid] = channel
            self._channel_owners[cid] = owner_id

            panel_msg_id = row[2]
            if panel_msg_id:
                try:
                    msg = await channel.fetch_message(panel_msg_id)
                    self._panel_messages[cid] = msg
                    await self._edit_panel(channel)
                except (discord.NotFound, discord.Forbidden):
                    pass

        log.info(f"{len(self._temp_channels)} Channel(s) got restored")

    def _is_temp(self, channel_id: int) -> bool:
        return channel_id in self._temp_channels

    async def _edit_panel(self, channel: discord.VoiceChannel) -> None:
        msg = self._panel_messages.get(channel.id)
        if not msg:
            return

        owner_id = self._channel_owners.get(channel.id)
        if not owner_id:
            return

        try:
            owner = channel.guild.get_member(owner_id)
            if not owner:
                return
            components = build_control_panel(channel, owner)
            view = discord.ui.DesignerView(*components)
            await msg.edit(view=view)
        except (discord.NotFound, discord.HTTPException):
            self._panel_messages.pop(channel.id, None)

    async def _delete_panel(self, channel_id: int) -> None:
        msg = self._panel_messages.pop(channel_id, None)
        if msg:
            with suppress(discord.NotFound, discord.Forbidden):
                await msg.delete()

    async def _create_temp_channel(self, member: discord.Member) -> None:
        guild = member.guild
        category = guild.get_channel(self.category_id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: OWNER_OVERWRITE,
        }

        channel = await guild.create_voice_channel(
            name=f"{member.display_name}'s Channel",
            category=category,
            bitrate=96000,
            user_limit=5,
            overwrites=overwrites,
            reason=f"TempVoice erstellt von {member.display_name}",
        )

        self._temp_channels[channel.id] = channel
        self._channel_owners[channel.id] = member.id
        await member.move_to(channel)

        components = build_control_panel(channel, member)
        view = discord.ui.DesignerView(*components)
        panel_msg = await channel.send(view=view)
        self._panel_messages[channel.id] = panel_msg
        await dbhandler.db.create_temp_channel(channel.id, member.id, panel_msg.id)
        log.info(f"Channel created: {channel.name} (Owner: {member})")

    async def _cleanup_channel(self, channel: discord.VoiceChannel) -> None:
        cid = channel.id
        self._temp_channels.pop(cid, None)
        self._channel_owners.pop(cid, None)

        with suppress(discord.NotFound, discord.Forbidden):
            await channel.delete(reason="TempVoice gelöscht weil Channel leer")

        await dbhandler.db.delete_temp_channel(cid)
        await dbhandler.db.cleanup_bans(cid)
        await dbhandler.db.cleanup_whitelist(cid)
        await self._delete_panel(cid)
        log.info(f"Channel deleted: {channel.name}")

    async def _transfer_ownership(
        self,
        channel: discord.VoiceChannel,
        old_owner: discord.Member,
        new_owner: discord.Member,
    ) -> None:
        await channel.set_permissions(old_owner, overwrite=None)
        await channel.set_permissions(new_owner, **OWNER_OVERWRITE._values)

        self._channel_owners[channel.id] = new_owner.id
        await dbhandler.db.change_owner(channel.id, new_owner.id)
        await self._edit_panel(channel)

        log.info(f"Ownership: {channel.name} -> {new_owner.display_name}")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        if (
            after.channel
            and after.channel.id == self.create_channel_id
            and (not before.channel or before.channel.id != self.create_channel_id)
        ):
            await self._create_temp_channel(member)
            return

        if (
            after.channel
            and self._is_temp(after.channel.id)
            and (not before.channel or before.channel.id != after.channel.id)
        ):
            await self._edit_panel(after.channel)

        if before.channel and self._is_temp(before.channel.id) and before.channel != after.channel:
            channel = before.channel
            remaining = [m for m in channel.members if not m.bot]

            if not remaining:
                await self._cleanup_channel(channel)
                return

            owner_id = self._channel_owners.get(channel.id)
            if owner_id and member.id == owner_id:
                new_owner = random.choice(remaining)
                await self._transfer_ownership(channel, member, new_owner)
                await channel.send(f"{new_owner.mention} hat nun die Owner Rechte.")
            else:
                await self._edit_panel(channel)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.component:
            return

        custom_id: str = interaction.data.get("custom_id", "")
        if not custom_id.startswith("tv_"):
            return

        parts = custom_id.split("_")
        if len(parts) < 3:
            return

        try:
            channel_id = int(parts[-1])
        except ValueError:
            return

        action = "_".join(parts[1:-1])

        channel = interaction.guild.get_channel(channel_id)
        if not channel or not self._is_temp(channel_id):
            await interaction.response.send_message("Dieser Channel existiert nicht mehr.", ephemeral=True)
            return

        owner_id = self._channel_owners.get(channel_id)
        if not owner_id or interaction.user.id != owner_id:
            await interaction.response.send_message("Nur der Channel Owner kann das Panel bedienen!", ephemeral=True)
            return

        match action:
            case "lock":
                await self._act_lock(interaction, channel)
            case "rename":
                await self._act_rename(interaction, channel)
            case "limit":
                await self._act_limit(interaction, channel)
            case "delete":
                await self._act_delete(interaction, channel)
            case "kick":
                await self._act_kick(interaction, channel)
            case "ban":
                await self._act_ban(interaction, channel)
            case "transfer":
                await self._act_transfer(interaction, channel)
            case "muteall":
                await self._act_mute_all(interaction, channel, mute=True)
            case "unmuteall":
                await self._act_mute_all(interaction, channel, mute=False)
            case "bans":
                await self._act_bans(interaction, channel)
            case "whitelist":
                await self._act_whitelist(interaction, channel)

    async def _act_lock(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        perms = channel.overwrites_for(channel.guild.default_role)
        currently_locked = perms.connect is False
        new_state = not currently_locked

        await channel.set_permissions(
            channel.guild.default_role,
            connect=None if not new_state else False,
        )

        label = "gesperrt 🔒" if new_state else "entsperrt 🔓"
        await interaction.response.send_message(f"Channel wurde **{label}**.", ephemeral=True)
        await self._edit_panel(channel)

    async def _act_rename(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        await interaction.response.send_modal(RenameModal(channel, self._edit_panel))

    async def _act_limit(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        await interaction.response.send_modal(LimitModal(channel, self._edit_panel))

    async def _act_delete(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        for m in list(channel.members):
            with suppress(discord.Forbidden, discord.HTTPException):
                await m.move_to(None)

        await interaction.response.send_message("Channel wird gelöscht...", ephemeral=True)
        cid = channel.id
        self._channel_owners.pop(cid, None)
        await self._cleanup_channel(channel)

    async def _act_kick(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        target = await self._resolve_member_from_select(interaction, channel)
        if not target:
            return

        await target.move_to(None, reason=f"Aus TempVoice gekickt von {interaction.user.display_name}")
        await interaction.response.send_message(f"{target.mention} wurde aus dem Channel gekickt.", ephemeral=True)
        await self._edit_panel(channel)

    async def _act_ban(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        values = interaction.data.get("values", [])
        if not values or values[0] == "none":
            await interaction.response.send_message("Kein User ausgewählt.", ephemeral=True)
            return

        target_id = int(values[0])
        target = interaction.guild.get_member(target_id)

        if not target:
            await interaction.response.send_message("User nicht gefunden.", ephemeral=True)
            return

        await channel.set_permissions(target, connect=False, reason=f"Gebannt von {interaction.user.display_name}")

        if target in channel.members:
            with suppress(discord.Forbidden, discord.HTTPException):
                await target.move_to(None)

        await dbhandler.db.add_ban(channel.id, target_id)
        await interaction.response.send_message(
            f"{target.mention} wurde gebannt und kann dem Channel nicht mehr betreten.", ephemeral=True
        )
        await self._edit_panel(channel)

    async def _act_transfer(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        values = interaction.data.get("values", [])
        if not values or values[0] == "none":
            await interaction.response.send_message("Kein User ausgewählt.", ephemeral=True)
            return

        new_owner_id = int(values[0])
        new_owner = interaction.guild.get_member(new_owner_id)

        if not new_owner:
            await interaction.response.send_message("User nicht gefunden.", ephemeral=True)
            return

        old_owner = interaction.user
        await self._transfer_ownership(channel, old_owner, new_owner)
        await interaction.response.send_message(f"Ownership wurde an {new_owner.mention} übertragen.", ephemeral=True)

        with suppress(discord.Forbidden):
            await new_owner.send(
                f"**{old_owner.display_name}** hat dir die Ownership von **{channel.name}** übertragen!"
            )

    async def _act_mute_all(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
        mute: bool,
    ) -> None:
        failed = 0
        for m in channel.members:
            if m.bot or m.id == interaction.user.id:
                continue
            try:
                await m.edit(
                    mute=mute, reason=f"{'Mute' if mute else 'Unmute'} All von {interaction.user.display_name}"
                )
            except (discord.Forbidden, discord.HTTPException):
                failed += 1

        label = "gemutet 🔇" if mute else "entmutet 🔊"
        note = f" ({failed} fehlgeschlagen)" if failed else ""
        await interaction.response.send_message(f"Alle Mitglieder wurden **{label}**{note}.", ephemeral=True)

    async def _act_bans(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        bans = await dbhandler.db.get_bans(channel.id)

        if not bans:
            await interaction.response.send_message("Keine gebannten User für diesen Channel.", ephemeral=True)
            return

        view = UnbanView(channel, bans, dbhandler.db, self._edit_panel)
        names = []
        for row in bans:
            m = interaction.guild.get_member(row[1])
            names.append(f"- **{m.display_name}**" if m else f"- User {row[1]}")

        await interaction.response.send_message(
            "🚫 **Ban-Liste** - Wähle User zum Entbannen aus:\n" + "\n".join(names),
            view=view,
            ephemeral=True,
        )

    async def _act_whitelist(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        perms = channel.overwrites_for(channel.guild.default_role)
        if perms.connect is not False:
            await interaction.response.send_message(
                "Die Whitelist ist nur aktiv wenn der Channel **gesperrt** ist.\n"
                "Sperre zuerst den Channel und öffne dann die Whitelist.",
                ephemeral=True,
            )
            return

        whitelist = await dbhandler.db.get_whitelist(channel.id)
        whitelisted_ids = [row[1] for row in whitelist] if whitelist else []

        view = WhitelistView(channel, whitelisted_ids, dbhandler.db, self._edit_panel)

        wl_str = (
            "\n".join(
                f"- **{channel.guild.get_member(uid).display_name}**"
                if channel.guild.get_member(uid)
                else f"- User {uid}"
                for uid in whitelisted_ids
            )
            or "*(leer)*"
        )

        await interaction.response.send_message(
            f"🔑 **Whitelist** - Wer darf trotz Sperre beitreten?\n{wl_str}",
            view=view,
            ephemeral=True,
        )

    async def _resolve_member_from_select(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
    ) -> discord.Member | None:
        values = interaction.data.get("values", [])
        if not values or values[0] == "none":
            await interaction.response.send_message("Kein User ausgewählt.", ephemeral=True)
            return None

        target_id = int(values[0])
        target = channel.guild.get_member(target_id)

        if not target:
            await interaction.response.send_message("User nicht gefunden.", ephemeral=True)
            return None

        if target not in channel.members:
            await interaction.response.send_message("User ist nicht mehr im Channel.", ephemeral=True)
            return None

        return target


def setup(bot: discord.Bot) -> None:
    bot.add_cog(TempVoice(bot))
