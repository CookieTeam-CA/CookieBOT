from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

import discord


class PaginatorButton(discord.ui.Button):
    def __init__(
        self,
        label: str,
        direction: int,
        style: discord.ButtonStyle = discord.ButtonStyle.gray,
        emoji: str | None = None,
    ):
        super().__init__(label=label, style=style, emoji=emoji)
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        view = cast("EmbedPaginator", self.view)
        view.current_page = (view.current_page + self.direction) % len(view.pages)
        await view._update(interaction)


class EmbedPaginator(discord.ui.View):
    """
    Universeller Embed-Paginator mit konfigurierbaren Buttons und optionalem Callback.

    Beispiel — Minimal:
        pages = build_pages(data, chunk_size=5, title="Meine Liste", builder=my_builder_fn)
        await EmbedPaginator(pages).send(ctx)

    Beispiel — Volle Konfiguration:
        await EmbedPaginator(
            pages,
            loop=True,
            show_jump_to_end=True,
            timeout=300,
            on_page_change=my_async_callback,
        ).send(ctx, ephemeral=True)
    """

    def __init__(
        self,
        pages: list[discord.Embed],
        *,
        loop: bool = False,
        show_jump_to_end: bool = False,
        timeout: float = 600,
        on_page_change: Callable[[int, discord.Interaction], Awaitable[None]] | None = None,
        prev_label: str = "◀",
        next_label: str = "▶",
        first_label: str = "⏮",
        last_label: str = "⏭",
        button_style: discord.ButtonStyle = discord.ButtonStyle.gray,
    ):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.loop = loop
        self.on_page_change = on_page_change

        if show_jump_to_end:
            self.add_item(PaginatorButton(first_label, direction=0, style=button_style))
            self._first_button: PaginatorButton | None = cast(PaginatorButton, self.children[-1])
            self._first_button.callback = self._jump_first
        else:
            self._first_button = None

        self.add_item(PaginatorButton(prev_label, direction=-1, style=button_style))
        self._prev_button = cast(PaginatorButton, self.children[-1])
        self._prev_button.callback = self._go_prev

        self.add_item(PaginatorButton(next_label, direction=1, style=button_style))
        self._next_button = cast(PaginatorButton, self.children[-1])
        self._next_button.callback = self._go_next

        if show_jump_to_end:
            self.add_item(PaginatorButton(last_label, direction=0, style=button_style))
            self._last_button: PaginatorButton | None = cast(PaginatorButton, self.children[-1])
            self._last_button.callback = self._jump_last
        else:
            self._last_button = None

        self._refresh_buttons()

    # --- Interne Navigation ---

    def _refresh_buttons(self):
        is_first = self.current_page == 0
        is_last = self.current_page == len(self.pages) - 1

        self._prev_button.disabled = is_first and not self.loop
        self._next_button.disabled = is_last and not self.loop

        if self._first_button:
            self._first_button.disabled = is_first
        if self._last_button:
            self._last_button.disabled = is_last

    async def _update(self, interaction: discord.Interaction):
        self._refresh_buttons()
        embed = self.pages[self.current_page]
        if self.on_page_change:
            await self.on_page_change(self.current_page, interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def _go_prev(self, interaction: discord.Interaction):
        self.current_page = (self.current_page - 1) % len(self.pages)
        await self._update(interaction)

    async def _go_next(self, interaction: discord.Interaction):
        self.current_page = (self.current_page + 1) % len(self.pages)
        await self._update(interaction)

    async def _jump_first(self, interaction: discord.Interaction):
        self.current_page = 0
        await self._update(interaction)

    async def _jump_last(self, interaction: discord.Interaction):
        self.current_page = len(self.pages) - 1
        await self._update(interaction)

    # --- Öffentliche API ---

    async def send(self, ctx, *, ephemeral: bool = False):
        """Sendet den Paginator als Antwort auf einen Slash-Command-Kontext."""
        await ctx.respond(embed=self.pages[0], view=self, ephemeral=ephemeral)

    async def send_to_channel(self, channel: discord.TextChannel) -> discord.Message:
        """Sendet den Paginator direkt in einen Channel."""
        return await channel.send(embed=self.pages[0], view=self)


def build_pages(
    data: list,
    *,
    title: str,
    builder: Callable[[int, list, discord.Embed], None],
    chunk_size: int = 5,
    color: discord.Color | None = None,
    footer_template: str = "Seite {page} von {total}",
) -> list[discord.Embed]:
    """
    Hilfsfunktion: Teilt eine Datenliste in Embed-Seiten auf.

    Args:
        data:            Die komplette Liste an Einträgen.
        title:           Titel jedes Embeds.
        builder:         Funktion(page_index, chunk, embed) → befüllt das Embed.
        chunk_size:      Wie viele Einträge pro Seite.
        color:           Embed-Farbe (Standard: discord.Color.blue()).
        footer_template: Platzhalter {page} und {total} verfügbar.

    Beispiel builder:
        def my_builder(i, chunk, embed):
            for row in chunk:
                embed.add_field(name=row.name, value=row.value, inline=False)
    """
    resolved_color = color if color is not None else discord.Color.blue()
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    total = len(chunks)
    pages = []

    for i, chunk in enumerate(chunks):
        embed = discord.Embed(title=title, color=resolved_color)
        embed.set_footer(text=footer_template.format(page=i + 1, total=total))
        builder(i, chunk, embed)
        pages.append(embed)

    return pages
