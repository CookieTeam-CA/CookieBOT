import asyncio
import configparser
import random

import discord
from discord.ext import commands
from ezcord import log

import dbhandler
from utils import safe_embed_channel_send


class FlagGuessingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parser = configparser.ConfigParser()
        self.parser.read("config.cfg")
        try:
            self.channel = int(self.parser["CHANNELS"]["flags"])
        except (KeyError, ValueError):
            log.error("FlagChannel ID not found in config.cfg!")
            self.channel = None

        self.flag_dict = {
            "af": ["Afghanistan", "Afghanistan"],
            "al": ["Albanien", "Albania"],
            "dz": ["Algerien", "Algeria"],
            "ad": ["Andorra", "Andorra"],
            "ao": ["Angola", "Angola"],
            "ag": ["Antigua und Barbuda", "Antigua and Barbuda"],
            "ar": ["Argentinien", "Argentina"],
            "am": ["Armenien", "Armenia"],
            "au": ["Australien", "Australia"],
            "at": ["Österreich", "Austria"],
            "az": ["Aserbaidschan", "Azerbaijan"],
            "bs": ["Bahamas", "Bahamas"],
            "bh": ["Bahrain", "Bahrain"],
            "bd": ["Bangladesch", "Bangladesh"],
            "bb": ["Barbados", "Barbados"],
            "by": ["Belarus", "Belarus", "Weißrussland", "Weissrussland"],
            "be": ["Belgien", "Belgium"],
            "bz": ["Belize", "Belize"],
            "bj": ["Benin", "Benin"],
            "bt": ["Bhutan", "Bhutan"],
            "bo": ["Bolivien", "Bolivia"],
            "ba": ["Bosnien und Herzegowina", "Bosnia and Herzegovina"],
            "bw": ["Botswana", "Botswana"],
            "br": ["Brasilien", "Brazil"],
            "bn": ["Brunei", "Brunei"],
            "bg": ["Bulgarien", "Bulgaria"],
            "bf": ["Burkina Faso", "Burkina Faso"],
            "bi": ["Burundi", "Burundi"],
            "cv": ["Kap Verde", "Cape Verde"],
            "kh": ["Kambodscha", "Cambodia"],
            "cm": ["Kamerun", "Cameroon"],
            "ca": ["Kanada", "Canada"],
            "cf": ["Zentralafrikanische Republik", "Central African Republic"],
            "td": ["Tschad", "Chad"],
            "cl": ["Chile", "Chile"],
            "cn": ["China", "China", "VR China", "Volksrepublik China"],
            "co": ["Kolumbien", "Colombia"],
            "km": ["Komoren", "Comoros"],
            "cd": ["Demokratische Republik Kongo", "Democratic Republic of the Congo", "DR Kongo", "D.R. Kongo"],
            "cg": ["Republik Kongo", "Republic of the Congo"],
            "cr": ["Costa Rica", "Costa Rica"],
            "ci": ["Elfenbeinküste", "Ivory Coast", "Cote d'ivoire"],
            "hr": ["Kroatien", "Croatia"],
            "cu": ["Kuba", "Cuba"],
            "cy": ["Zypern", "Cyprus"],
            "cz": ["Tschechien", "Czech Republic"],
            "dk": ["Dänemark", "Denmark"],
            "dj": ["Dschibuti", "Djibouti"],
            "dm": ["Dominica", "Dominica"],
            "do": ["Dominikanische Republik", "Dominican Republic"],
            "ec": ["Ecuador", "Ecuador"],
            "eq": ["Ägypten", "Egypt"],
            "sv": ["El Salvador", "El Salvador"],
            "gq": ["Äquatorialguinea", "Equatorial Guinea"],
            "er": ["Eritrea", "Eritrea"],
            "ee": ["Estland", "Estonia"],
            "sz": ["Eswatini", "Eswatini"],
            "et": ["Äthiopien", "Ethiopia"],
            "fj": ["Fidschi", "Fiji"],
            "fi": ["Finnland", "Finland"],
            "fr": ["Frankreich", "France"],
            "ga": ["Gabun", "Gabon"],
            "gm": ["Gambia", "Gambia"],
            "ge": ["Georgien", "Georgia"],
            "de": ["Deutschland", "Germany"],
            "gh": ["Ghana", "Ghana"],
            "gr": ["Griechenland", "Greece"],
            "gd": ["Grenada", "Grenada"],
            "gt": ["Guatemala", "Guatemala"],
            "gn": ["Guinea", "Guinea"],
            "gw": ["Guinea-Bissau", "Guinea-Bissau"],
            "gy": ["Guyana", "Guyana"],
            "ht": ["Haiti", "Haiti"],
            "hn": ["Honduras", "Honduras"],
            "hu": ["Ungarn", "Hungary"],
            "is": ["Island", "Iceland"],
            "in": ["Indien", "India"],
            "id": ["Indonesien", "Indonesia"],
            "ir": ["Iran", "Iran"],
            "iq": ["Irak", "Iraq"],
            "ie": ["Irland", "Ireland"],
            "il": ["Israel", "Israel"],
            "it": ["Italien", "Italy"],
            "jm": ["Jamaika", "Jamaica"],
            "jp": ["Japan", "Japan"],
            "jo": ["Jordanien", "Jordan"],
            "kz": ["Kasachstan", "Kazakhstan"],
            "ke": ["Kenia", "Kenya"],
            "ki": ["Kiribati", "Kiribati"],
            "kp": ["Nordkorea", "North Korea"],
            "kr": ["Südkorea", "South Korea"],
            "xk": ["Kosovo", "Kosovo"],
            "kw": ["Kuwait", "Kuwait"],
            "kg": ["Kirgisistan", "Kyrgyzstan", "Kirgistan", "Kirgisien"],
            "la": ["Laos", "Laos"],
            "lv": ["Lettland", "Latvia"],
            "lb": ["Libanon", "Lebanon"],
            "ls": ["Lesotho", "Lesotho"],
            "lr": ["Liberia", "Liberia"],
            "ly": ["Libyen", "Libya"],
            "li": ["Liechtenstein", "Liechtenstein"],
            "lt": ["Litauen", "Lithuania"],
            "lu": ["Luxemburg", "Luxembourg"],
            "mk": ["Nordmazedonien", "North Macedonia"],
            "mg": ["Madagaskar", "Madagascar"],
            "mw": ["Malawi", "Malawi"],
            "my": ["Malaysia", "Malaysia"],
            "mv": ["Malediven", "Maldives"],
            "ml": ["Mali", "Mali"],
            "mt": ["Malta", "Malta"],
            "mh": ["Marshallinseln", "Marshall Islands"],
            "mr": ["Mauretanien", "Mauritania"],
            "mu": ["Mauritius", "Mauritius"],
            "mx": ["Mexiko", "Mexico"],
            "fm": ["Mikronesien", "Micronesia"],
            "md": ["Moldawien", "Moldova", "Moldau"],
            "mc": ["Monaco", "Monaco"],
            "mn": ["Mongolei", "Mongolia"],
            "me": ["Montenegro", "Montenegro"],
            "ma": ["Marokko", "Morocco"],
            "mz": ["Mosambik", "Mozambique"],
            "mm": ["Myanmar", "Myanmar"],
            "na": ["Namibia", "Namibia"],
            "nr": ["Nauru", "Nauru"],
            "np": ["Nepal", "Nepal"],
            "nl": ["Niederlande", "Netherlands"],
            "nz": ["Neuseeland", "New Zealand"],
            "ni": ["Nicaragua", "Nicaragua"],
            "ne": ["Niger", "Niger"],
            "ng": ["Nigeria", "Nigeria"],
            "no": ["Norwegen", "Norway"],
            "om": ["Oman", "Oman"],
            "pk": ["Pakistan", "Pakistan"],
            "pw": ["Palau", "Palau"],
            "ps": ["Palästina", "Palestine"],
            "pa": ["Panama", "Panama"],
            "pg": ["Papua-Neuguinea", "Papua New Guinea"],
            "py": ["Paraguay", "Paraguay"],
            "pe": ["Peru", "Peru"],
            "ph": ["Philippinen", "Philippines"],
            "pl": ["Polen", "Poland"],
            "pt": ["Portugal", "Portugal"],
            "qa": ["Katar", "Qatar"],
            "ro": ["Rumänien", "Romania"],
            "ru": ["Russland", "Russia"],
            "rw": ["Ruanda", "Rwanda"],
            "kn": ["St. Kitts und Nevis", "Saint Kitts and Nevis"],
            "lc": ["St. Lucia", "Saint Lucia"],
            "vc": ["St. Vincent und die Grenadinen", "Saint Vincent and the Grenadines"],
            "ws": ["Samoa", "Samoa"],
            "sm": ["San Marino", "San Marino"],
            "st": ["Sao Tome und Principe", "Sao Tome and Principe"],
            "sa": ["Saudi-Arabien", "Saudi Arabia", "Saudi Arabien"],
            "sn": ["Senegal", "Senegal"],
            "rs": ["Serbien", "Serbia"],
            "sc": ["Seychellen", "Seychelles"],
            "sl": ["Sierra Leone", "Sierra Leone"],
            "sg": ["Singapur", "Singapore"],
            "sk": ["Slowakei", "Slovakia"],
            "si": ["Slowenien", "Slovenia"],
            "sb": ["Salomonen", "Solomon Islands"],
            "so": ["Somalia", "Somalia"],
            "za": ["Südafrika", "South Africa"],
            "ss": ["Südsudan", "South Sudan"],
            "es": ["Spanien", "Spain"],
            "lk": ["Sri Lanka", "Sri Lanka"],
            "sd": ["Sudan", "Sudan"],
            "sr": ["Suriname", "Suriname"],
            "se": ["Schweden", "Sweden"],
            "ch": ["Schweiz", "Switzerland"],
            "sy": ["Syrien", "Syria"],
            "tw": ["Taiwan", "Taiwan", "Republik China"],
            "tj": ["Tadschikistan", "Tajikistan"],
            "tz": ["Tansania", "Tanzania"],
            "th": ["Thailand", "Thailand"],
            "tl": ["Osttimor", "Timor-Leste"],
            "tg": ["Togo", "Togo"],
            "to": ["Tonga", "Tonga"],
            "tt": ["Trinidad und Tobago", "Trinidad and Tobago"],
            "tn": ["Tunesien", "Tunisia"],
            "tr": ["Türkei", "Turkey"],
            "tm": ["Turkmenistan", "Turkmenistan"],
            "tv": ["Tuvalu", "Tuvalu"],
            "ug": ["Uganda", "Uganda"],
            "ua": ["Ukraine", "Ukraine"],
            "ae": ["Vereinigte Arabische Emirate", "United Arab Emirates", "UAE"],
            "gb": ["Vereinigtes Königreich", "United Kingdom", "UK"],
            "us": ["USA", "United States of America"],
            "uy": ["Uruguay", "Uruguay"],
            "uz": ["Usbekistan", "Uzbekistan"],
            "vu": ["Vanuatu", "Vanuatu"],
            "va": ["Vatikanstadt", "Vatican City", "Vatikan"],
            "ve": ["Venezuela", "Venezuela"],
            "vn": ["Vietnam", "Vietnam"],
            "ye": ["Jemen", "Yemen"],
            "zm": ["Sambia", "Zambia"],
            "zw": ["Simbabwe", "Zimbabwe"],
        }
        self.current_flag = None
        self.message = None
        self.cooldown = False
        self.count = 0

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("flagguess.py is ready")
        await self.start_new_game()

    async def start_new_game(self):
        await asyncio.sleep(1)  # war auf 15s
        self.cooldown = False
        self.current_flag = random.choice(list(self.flag_dict.keys()))
        log.debug(f"the flag is {self.current_flag}")
        file = discord.File(f"img/flags/{self.current_flag}" + ".png", filename="flag.png")
        embed = discord.Embed(title="Neue Flagge!", color=discord.Color.random())
        embed.set_image(url="attachment://flag.png")
        await safe_embed_channel_send(self.bot, self.channel, embed=embed, file=file)

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.cooldown:
            return
        if message.author == self.bot.user:
            return
        if message.channel.id == self.channel and self.current_flag is not None:
            await dbhandler.db.insert_user("flag_stats", "user_id", message.author.id)

            if message.content.lower() in [name.lower() for name in self.flag_dict[self.current_flag]]:
                await dbhandler.db.update_flag_stats(message.author.id, True)
                result = await dbhandler.db.get_one_row("flag_stats", "user_id", message.author.id)
                embed = discord.Embed(
                    title="Richtig!",
                    description=f"**{message.author.display_name}** hat die Flagge **{message.content}** richtig "
                                f"erraten.",
                    color=discord.Color.green(),
                )

                if result[3] > 3:
                    embed.set_footer(text=f"Deine neue Streak ist {result[3]}")
                else:
                    embed.set_footer(text=f"Deine Gewinnchance: {round(result[1] / result[2] * 100)}%")
                    log.info(f"{message.author} hat eine Flagge erraten.")
                await message.add_reaction("✅")
                await safe_embed_channel_send(self.bot, message.channel.id, embed=embed)
                self.cooldown = True
                await self.start_new_game()
            else:
                await message.add_reaction("❌")
                result = await dbhandler.db.get_one_row("flag_stats", "user_id", message.author.id)
                await dbhandler.db.update_flag_stats(message.author.id, False)

                embed = discord.Embed(
                    title="Streak kaputt!",
                    color=discord.Color.red(),
                    description=f"Du hast deine **{result[3]}er** Streak verloren.",
                )
                if result[3] > 2:
                    await safe_embed_channel_send(self.bot, message.channel.id, embed=embed)

                # self.count += 1
                # if self.count == 5:
                #    await message.channel.send("Du kannst /skip benutzen, um die Flagge zu überspringen.")
                #    self.count = 0


# add /skip command


def setup(bot):
    bot.add_cog(FlagGuessingCog(bot))
