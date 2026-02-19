import asyncio
import configparser
import json
import time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from ezcord import log
from ezcord.internal.dc import slash_command

import dbhandler
import utils


class ButtonPaginator(discord.ui.View):
    def __init__(self, pages):
        super().__init__(timeout=600)
        self.pages = pages
        self.current_page = 0

    async def update_view(self, interaction: discord.Interaction):
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.pages) - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.gray)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page -= 1
        await self.update_view(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.gray)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page += 1
        await self.update_view(interaction)


class OneWordChallenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.de = ZoneInfo("Europe/Berlin")
        self.parser = configparser.ConfigParser()
        self.parser.read("config.cfg")
        try:
            self.channel = int(self.parser["CHANNELS"]["one_word"])
        except (KeyError, ValueError):
            log.error("OneWord ID not found in config.cfg!")
            self.channel = None
        self.id = None
        self.words = []
        self.last_author = None

    @commands.Cog.listener()
    async def on_ready(self):
        last_game_state = await dbhandler.db.get_latest_row("one_word", "id")

        if last_game_state and last_game_state[3] == 0:
            self.id = last_game_state[0]

            try:
                self.words = json.loads(last_game_state[1]) if last_game_state[1] else []
            except (json.JSONDecodeError, TypeError):
                log.warning("Game save couldn't load. Starting new.")
                self.words = []

            self.last_author = last_game_state[2]
            log.debug("one_word restored last game state")
        else:
            log.debug("one_word no active game found.")

        log.info("one_word.py is ready")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.channel.id != self.channel:
            return
        if self.last_author == message.author.id:
            msg = await message.reply(
                "Du darfst nicht 2 Wörter hintereinander schreiben.",
                mention_author=False,
            )
            await utils.safe_delete(message)
            await asyncio.sleep(5)
            await utils.safe_delete(msg)
            return

        content = message.content.strip()

        if len(content.split()) == 1:
            self.words.append(content)
            self.last_author = message.author.id

            if self.id is None:
                self.id = int(time.time() * 1000)
                await dbhandler.db.new_row_one_word(self.id, json.dumps(self.words), self.last_author)
            else:
                await dbhandler.db.update_one_word(json.dumps(self.words), self.last_author, self.id, 0)

            await message.add_reaction("✅")

            if content.endswith((".", "?", "!")):
                embed = discord.Embed(
                    title="Der Fertige Satz ist:", description=(" ".join(self.words)), color=discord.Color.random()
                )
                embed.set_footer(text="Nutze /one_word_list um vorherige Sätze anzuschauen!")
                await message.channel.send(embed=embed)
                await dbhandler.db.update_one_word(json.dumps(self.words), self.last_author, self.id, 1)
                self.id = None
                self.words = []
        else:
            msg = await message.reply("Du darfst nur ein Wort schreiben.", mention_author=False)
            await utils.safe_delete(message)
            await asyncio.sleep(5)
            await utils.safe_delete(msg)

    @slash_command()
    async def one_word_list(self, ctx):
        log.debug(f"{ctx.author.name} used /one_word_list")
        await ctx.defer()
        data = await dbhandler.db.get_finished_games()

        if not data:
            await ctx.respond("Es wurden noch keine Sätze vervollständigt.", ephemeral=True)
            return

        embeds = []
        chunk_size = 5
        chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

        for i, chunk in enumerate(chunks):
            embed = discord.Embed(title="📚 One Word Verlauf", color=discord.Color.blue())
            embed.set_footer(text=f"Seite {i + 1} von {len(chunks)}")

            for row in chunk:
                game_id, json_words, last_author_id = row[0], row[1], row[2]

                try:
                    words_list = json.loads(json_words) if json_words else []
                    sentence = " ".join(words_list)
                except json.JSONDecodeError:
                    sentence = "*Fehler beim Laden*"

                embed.add_field(
                    name=f"Satz #{game_id}", value=f"💬 {sentence}\n🏁 Beendet von: <@{last_author_id}>", inline=False
                )

            embeds.append(embed)

        view = ButtonPaginator(embeds)
        view.update_buttons()
        await ctx.respond(embed=embeds[0], view=view)


def setup(bot):
    bot.add_cog(OneWordChallenge(bot))
