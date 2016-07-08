from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import discord
import requests
import asyncio
import os
import datetime
import json
from __main__ import send_cmd_help

class hpapi():
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/hpapi/hpapi.json'
        settings = fileIO(self.settings_file, 'load')
        self.hpapi_key = settings['API_KEY']
        self.payload = {}
        self.payload["key"] = self.hpapi_key

    def get_json(self, url):
        return requests.get(url).json()

    @commands.group(pass_context=True, no_pm=True, name="hp")
    async def _hpapi(self, ctx):
        """Get data from the Hypixel API"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_hpapi.command(pass_context=True, no_pm=True, name='booster')
    async def _booster(self, ctx, *game: str):
        """Get active boosters. A game can be specified, in which case only the active booster for that game will be shown"""
        data = {}
        url = "https://api.hypixel.net/boosters?key=" + self.hpapi_key
        data = self.get_json(url)

        message = ""
        print(data)
        if data["success"]:
            booster_list = data["boosters"]
            if not game:
                for item in booster_list:
                    if item["length"] < item["originalLength"]:
                        game_name = ""
                        remaining = str(datetime.timedelta(seconds=item["length"]))
                        name_get_url = "https://api.mojang.com/user/profiles/" + item["purchaserUuid"] + "/names"
                        name_data = self.get_json(name_get_url)
                        name = name_data[-1]["name"]
                        if item["gameType"] == 2:
                            game_name = "Quakecraft"
                        elif item["gameType"] == 3:
                            game_name = "Walls"
                        elif item["gameType"] == 4:
                            game_name = "Paintball"
                        elif item["gameType"] == 5:
                            game_name = "Blitz Survival Games"
                        elif item["gameType"] == 6:
                            game_name = "The TNT Games"
                        elif item["gameType"] == 7:
                            game_name = "VampireZ"
                        elif item["gameType"] == 13:
                            game_name = "Mega Walls"
                        elif item["gameType"] == 14:
                            game_name = "Arcade"
                        elif item["gameType"] == 17:
                            game_name = "Arena Brawl"
                        elif item["gameType"] == 21:
                            game_name = "Cops and Crims"
                        elif item["gameType"] == 20:
                            game_name = "UHC Champions"
                        elif item["gameType"] == 23:
                            game_name = "Warlords"
                        elif item["gameType"] == 24:
                            game_name = "Smash Heroes"
                        elif item["gameType"] == 25:
                            game_name = "Turbo Kart Racers"
                        elif item["gameType"] == 51:
                            game_name = "SkyWars"
                        elif item["gameType"] == 52:
                            game_name = "Crazy Walls"
                        elif item["gameType"] == 54:
                            game_name = "Speed UHC"

                        message += name + "\'s " + game_name + " booster has " + remaining + " left\n"
            else:
                game_name = ""
                print(game)
                for word in game:
                    game_name = game_name + word + " "
                game_name = game_name.lower().strip()
                gameType = None

                if game_name == "Quakecraft".lower():
                    gameType = 2
                    game_name = "Quakecraft"
                elif game_name == "Walls".lower():
                    gameType = 3
                    game_name = "Walls"
                elif game == "Paintball".lower():
                    gameType = 4
                    game_name = "Paintball"
                elif game_name == "Blitz Survival Games".lower():
                    gameType = 5
                    game_name = "Blitz Survival Games"
                elif game_name == "The TNT Games".lower():
                    gameType = 6
                    game_name = "The TNT Games"
                elif game_name == "VampireZ".lower():
                    gameType = 7
                    game_name = "VampireZ"
                elif game_name == "Mega Walls".lower():
                    gameType = 13
                    game_name = "Mega Walls"
                elif game_name == "Arcade".lower():
                    gameType= 14
                    game_name = "Arcade"
                elif game_name == "Arena Brawl".lower():
                    gameType = 17
                    game_name = "Arena Brawl"
                elif game_name == "Cops and Crims".lower():
                    gameType = 21
                    game_name = "Cops and Crims"
                elif game_name == "UHC Champions".lower():
                    gameType = 20
                    game_name = "UHC Champions"
                elif game_name == "Warlords".lower():
                    gameType = 23
                    game_name = "Warlords"
                elif game_name == "Smash Heroes".lower():
                    gameType = 24
                    game_name = "Smash Heroes"
                elif game_name == "Turbo Kart Racers".lower():
                    gameType = 25
                    game_name = "Turbo Kart Racers"
                elif game_name == "SkyWars".lower():
                    gameType = 51
                    game_name = "SkyWars"
                elif game_name == "Crazy Walls".lower():
                    gameType = 52
                    game_name = "Crazy Walls"
                elif game_name == "Speed UHC".lower():
                    gameType = 54
                    game_name = "Speed UHC"

                for item in booster_list:
                    if item["length"] < item["originalLength"] and item["gameType"] == gameType:
                        remaining = str(datetime.timedelta(seconds=item["length"]))
                        name_get_url = "https://api.mojang.com/user/profiles/" + item["purchaserUuid"] + "/names"
                        name_data = self.get_json(name_get_url)
                        name = name_data[-1]["name"]
                        message += name + "\'s " + game_name + " booster has " + remaining + " left\n"
        else:
            message = "An error occurred in getting the data\n\n" + json.dumps(data)
        await self.bot.say('```{}```'.format(message))

    @_hpapi.command(pass_context=True, name='key')
    @checks.is_owner()
    async def _apikey(self, context, *key: str):
        """Sets the Hypixel API key - owner only"""
        settings = fileIO(self.settings_file, "load")
        if key:
            settings['API_KEY'] = key[0]
            fileIO(self.settings_file, "save", settings)
            await self.bot.say('```API key set```')

def check_folder():
    if not os.path.exists("data/hpapi"):
        print("Creating data/hpapi folder")
        os.makedirs("data/hpapi")

def check_file():
    data = {}
    data["API_KEY"] = ''
    f = "data/hpapi/hpapi.json"
    if not fileIO(f, "check"):
        print("Creating default hpapi.json...")
        fileIO(f, "save", data)

def setup(bot):
    check_folder()
    check_file()
    n = hpapi(bot)
    bot.add_cog(n)
