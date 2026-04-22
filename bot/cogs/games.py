import asyncio
import random

from discord import ButtonStyle, Color, Embed, Interaction, Option, ui
from discord.ext import commands
from discord.ui import Button, View
from ezcord import log
from ezcord.internal.dc import slash_command

from bot.db.handler import db


async def cookies_check(ctx, bet):
    bet = int(bet)
    if bet <= 0:
        return await ctx.respond("Du musst mindestens 1 Cookie setzen.", ephemeral=True)

    bank = await db.get_cookies(ctx.author.id)
    if bank < bet:
        return await ctx.respond(f"Du hast nicht genügend Cookies. (Guthaben: **{bank}** Cookies)", ephemeral=True)


card_values = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 10,
    "Q": 10,
    "K": 10,
    "A": 11,
}


def create_deck():
    deck = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"] * 4
    random.shuffle(deck)
    return deck


def calculate_hand(hand):
    value = sum(card_values[card] for card in hand)
    if value > 21 and "A" in hand:
        value -= 10
    return value


class BlackjackView(View):
    def __init__(self, ctx, deck, player_hand, dealer_hand, bet, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.bet = bet
        self.bot = bot

    async def show_hands(self):
        player_value = calculate_hand(self.player_hand)
        dealer_value = calculate_hand(self.dealer_hand[:1])
        embed = Embed(
            title="Blackjack",
            description=f"Du hast: {', '.join(self.player_hand)} (Wert: {player_value})\n"
            f"Dealer zeigt: {', '.join(self.dealer_hand[:1])} (Wert: {dealer_value})",
            color=Color.blue(),
        )
        return embed

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "Nur der Spieler, der den Befehl ausgeführt hat, kann die Buttons verwenden!",
                ephemeral=True,
            )
            return False
        return True

    @ui.button(label="Hit", style=ButtonStyle.green)
    async def hit(self, button: Button, interaction: Interaction):
        self.player_hand.append(self.deck.pop())
        if calculate_hand(self.player_hand) > 21:
            embed = Embed(
                title="Verloren",
                description="Du bist über 21. Du verlierst!",
                color=Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            await interaction.response.edit_message(embed=await self.show_hands())

    @ui.button(label="Stand", style=ButtonStyle.red)
    async def stand(self, button: Button, interaction: Interaction):
        player_value = calculate_hand(self.player_hand)

        while calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        dealer_value = calculate_hand(self.dealer_hand)
        embed = Embed(
            title="Ergebnis",
            description=f"Dealer hat: {', '.join(self.dealer_hand)} (Wert: {dealer_value})\n"
            f"Du hast: {', '.join(self.player_hand)} (Wert: {player_value})",
            color=Color.blue(),
        )

        if dealer_value > 21 or player_value > dealer_value:
            embed.add_field(name="Glückwunsch!", value=f"Du hast **{self.bet} Cookies** gewonnen!")
            await db.add_cookies(self.ctx.author.id, self.bet * 2)
        elif player_value < dealer_value:
            embed.add_field(name="Schade!", value=f"Du hast **{self.bet} Cookies** verloren.")
        else:
            embed.add_field(name="Unentschieden!", value="Du hast weder Cookies verloren noch gewonnen.")

        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("games.py is ready")

    @slash_command()
    async def coinflip(self, ctx, coin: Option(str, required=True, choices=["Kopf", "Zahl"]), cookies: int):  # type: ignore
        if await cookies_check(ctx, cookies):
            return

        msg = await ctx.respond("🪙 Die Münze wird geworfen...")
        result = random.choice(["Kopf", "Zahl"])
        choice = "heads" if coin == "Kopf" else "tails"
        await asyncio.sleep(0.5)

        won = coin == result

        if won:
            await db.coinflip_win(ctx.author.id, choice, cookies)
            await db.add_cookies(ctx.author.id, cookies)
        else:
            await db.coinflip_loss(ctx.author.id, choice, cookies)
            await db.remove_cookies(ctx.author.id, cookies)

        stats = await db.get_coinflip_stats(ctx.author.id)
        new_balance = await db.get_cookies(ctx.author.id)

        # stats: [user_id, heads, tails, heads_wins, tails_wins, current_streak, best_streak, cookies_loss, cookies_won]
        total_flips = stats[1] + stats[2]
        total_wins = stats[3] + stats[4]
        winrate = round(total_wins / total_flips * 100) if total_flips > 0 else 0
        net_profit = stats[8] - stats[7]
        net_str = f"+{net_profit}" if net_profit >= 0 else str(net_profit)

        if won:
            embed = Embed(title=f"Gewonnen! {result}", color=Color.green())
            embed.add_field(name="Gewinn", value=f"+**{cookies}** Cookies", inline=True)
        else:
            embed = Embed(title=f"Verloren! {result}", color=Color.red())
            embed.add_field(name="Verlust", value=f"-**{cookies}** Cookies", inline=True)

        embed.add_field(name="Guthaben", value=f"**{new_balance}** Cookies", inline=True)
        embed.add_field(name="🔥 Streak", value=f"**{stats[5]}**", inline=True)
        embed.add_field(name="🏆 Best Streak", value=f"**{stats[6]}**", inline=True)
        embed.add_field(name="📊 Winrate", value=f"**{winrate}%**", inline=True)
        embed.add_field(name="💰 Profit", value=f"**{net_str}** Cookies", inline=True)

        await msg.edit(content=None, embed=embed)

    @slash_command()
    async def blackjack(self, ctx, bet: int):
        if bet <= 0:
            return await ctx.respond("Du musst mindestens 1 Cookie setzen.", ephemeral=True)
        if await db.remove_cookies(ctx.author.id, bet) == 0:
            return await ctx.respond("Du hast nicht genügend Cookies.", ephemeral=True)

        deck = create_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        view = BlackjackView(ctx, deck, player_hand, dealer_hand, bet, self.bot)
        await ctx.respond(embed=await view.show_hands(), view=view)


def setup(bot):
    bot.add_cog(Games(bot))
