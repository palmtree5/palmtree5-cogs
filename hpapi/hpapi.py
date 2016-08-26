"""Extension for Red-DiscordBot"""
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import aiohttp
import asyncio
import hashlib
import os
from copy import deepcopy
import datetime as dt
import json
from __main__ import send_cmd_help


class hpapi():
    """Class for Hypixel API module for Red-DiscordBot"""
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/hpapi/hpapi.json'
        settings = fileIO(self.settings_file, 'load')
        self.hpapi_key = settings['API_KEY']
        self.games = settings['games']
        self.payload = {}
        self.payload["key"] = self.hpapi_key

    async def get_json(self, url):
        async with aiohttp.get(url) as r:
            ret = await r.json()
        return ret

    def get_time(self, ms):
        time = dt.datetime.utcfromtimestamp(ms/1000)
        return time.strftime('%m-%d-%Y %H:%M:%S') + "\n"

    @commands.group(pass_context=True, name="hp")
    async def _hpapi(self, ctx):
        """Get data from the Hypixel API"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_hpapi.command(pass_context=True, no_pm=True, name='booster')
    async def _booster(self, ctx, *game: str):
        """
        Get active boosters. A game can be specified, in which case only the
        active booster for that game will be shown
        """
        data = {}
        url = "https://api.hypixel.net/boosters?key=" + self.hpapi_key
        data = await self.get_json(url)

        message = ""
        if data["success"]:
            booster_list = data["boosters"]
            if not game:
                for item in booster_list:
                    if item["length"] < item["originalLength"]:
                        game_name = ""
                        remaining = \
                            str(dt.timedelta(seconds=item["length"]))
                        name_url = "https://api.mojang.com/user/profiles/" \
                            + item["purchaserUuid"] + "/names"
                        name_data = await self.get_json(name_url)
                        name = name_data[-1]["name"]
                        for game in self.games:
                            if item["gameType"] == game["id"]:
                                game_name = game["name"]
                                break
                        message += name + "\'s " + game_name + \
                            " booster has " + remaining + " left\n"

            else:
                game_n = " ".join(game)
                game_name = game_n.lower().strip()
                gameType = None
                for game in self.games:
                    if game_name = game["name"].lower():
                        game_name = game["name"]
                        gameType = game["id"]
                        break
                for item in booster_list:
                    if item["length"] < item["originalLength"] and \
                            item["gameType"] == gameType:
                        remaining = \
                           str(dt.timedelta(seconds=item["length"]))
                        name_get_url = \
                            "https://api.mojang.com/user/profiles/" + \
                            item["purchaserUuid"] + "/names"

                        name_data = self.get_json(name_get_url)
                        name = name_data[-1]["name"]
                        message += name + "\'s " + game_name + \
                            " booster has " + remaining + " left\n"
        else:
            message = "An error occurred in getting the data"
        await self.bot.say('```{}```'.format(message))

    @_hpapi.command(pass_context=True, name='player')
    async def _player(self, ctx, name):
        """Gets data about the specified player"""

        message = ""
        url = "https://api.hypixel.net/player?key=" + \
            self.hpapi_key + "&name=" + name

        data = self.get_json(url)
        if data["success"]:
            player_data = data["player"]
            message = "Player data for " + name + "\n"
            if "buildTeam" in player_data:
                if player_data["buildTeam"] is True:
                    message += "Rank: Build Team\n"
            elif "rank" in player_data:
                if player_data["rank"] == "ADMIN":
                    message += "Rank: Admin\n"
                elif player_data["rank"] == "MODERATOR":
                    message += "Rank: Moderator\n"
                elif player_data["rank"] == "HELPER":
                    message += "Rank: Helper\n"
            elif "newPackageRank" in player_data:
                if player_data["newPackageRank"] == "MVP_PLUS":
                    message += "Rank: MVP+\n"
                elif player_data["newPackageRank"] == "MVP":
                    message += "Rank: MVP\n"
                elif player_data["newPackageRank"] == "VIP_PLUS":
                    message += "Rank: VIP+\n"
                elif player_data["newPackageRank"] == "VIP":
                    message += "Rank: VIP\n"
            elif "packageRank" in player_data:
                if player_data["packageRank"] == "MVP_PLUS":
                    message += "Rank: MVP+\n"
                elif player_data["packageRank"] == "MVP":
                    message += "Rank: MVP\n"
                elif player_data["packageRank"] == "VIP_PLUS":
                    message += "Rank: VIP+\n"
                elif player_data["packageRank"] == "VIP":
                    message += "Rank: VIP\n"
            elif bool(player_data):
                message += "Rank: None\n"
            else:
                message = "That player has never logged into Hypixel"
            message += "Level: " + str(player_data["networkLevel"]) + "\n"
            message += "First login (UTC): " + \
                self.get_time(player_data["firstLogin"]) + "\n"
            message += "Last login (UTC): " + \
                self.get_time(player_data["lastLogin"]) + "\n"
            if "vanityTokens" in player_data:
                message += "Credits: " + str(player_data["vanityTokens"]) \
                    + "\n"
            else:
                message += "Credits: 0\n"
        else:
            message = "An error occurred in getting the data."
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
    f = "data/hpapi/hpapi.json"
    games = 
        [
            {"id": 2, "name": "Quakecraft"},
            {"id": 3, "name": "Walls"},
            {"id": 4, "name": "Paintball"},
            {"id": 5, "name": "Blitz Survival Games"},
            {"id": 6, "name": "The TNT Games"},
            {"id": 7, "name": "VampireZ"},
            {"id": 13, "name": "Mega Walls"},
            {"id": 14, "name": "Arcade"},
            {"id": 17, "name": "Arena Brawl"},
            {"id": 21, "name": "Cops and Crims"},
            {"id": 20, "name": "UHC Champions"},
            {"id": 23, "name": "Warlords"},
            {"id": 24, "name": "Smash Heroes"},
            {"id": 25, "name": "Turbo Kart Racers"},
            {"id": 51, "name": "SkyWars"},
            {"id": 52, "name": "Crazy Walls"},
            {"id": 54, "name": "Speed UHC"}
        ]
    data = {}
    data["API_KEY"] = ''
    data["games"] = games
        
    if not fileIO(f, "check"):
        print("Creating default hpapi.json...")
        fileIO(f, "save", data)
    else:
        cur_settings = fileIO(f, "load")
        cur_games = cur_settings["games"]
        for game in games:
            game_exists = False
            for g in cur_games:
                if g["id"] == game["id"]:
                    game_exists = True
            if not game_exists:
                cur_games.append(deepcopy(game))
        print("Updating hpapi.json...")
        cur_settings["games"] = cur_games
        fileIO(f, save, cur_settings)

def setup(bot):
    check_folder()
    check_file()
    n = hpapi(bot)
    bot.add_cog(n)
