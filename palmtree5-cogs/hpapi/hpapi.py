"""Extension for Red-DiscordBot"""
from discord.ext import commands
import discord
from random import choice as randchoice
from redbot.core import Config, checks, data_manager
import aiohttp
from datetime import datetime as dt
import datetime
import os
import json
import aiofiles
import asyncio


numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


class Hpapi:
    """Cog for getting info from Hypixel's API"""
    default_global = {
        "api_key": ""
    }

    def __init__(self):
        self.settings = Config.get_conf(
            self, identifier=59595922, force_registration=True
        )
        self.settings.register_global(**self.default_global)
        self.session = aiohttp.ClientSession()
        loop = asyncio.get_event_loop()
        loop.create_task(self.achievements_getter())
        self.achievements = loop.create_task(self.load_achievements())
        self.games = loop.create_task(self.load_games())

    async def load_achievements(self):
        async with aiofiles.open(os.path.join(data_manager.cog_data_path(self), "achievements.json")) as f:
            content = json.loads(await f.read())
        return content

    async def load_games(self):
        async with aiofiles.open(os.path.join(data_manager.bundled_data_path(self), "games.json")) as f:
            content = json.loads(await f.read())
        return content

    async def get_json(self, url):
        async with self.session.get(url) as r:
            ret = await r.json()
        return ret

    def get_time(self, ms):
        time = dt.utcfromtimestamp(ms/1000)
        return time.strftime('%m-%d-%Y %H:%M:%S') + "\n"

    async def booster_menu(self, ctx, booster_list: list,
                           message: discord.Message=None,
                           page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        s = booster_list[page]
        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                     for x in range(6)])
        colour = int(colour, 16)
        created_at = dt.utcfromtimestamp(s["dateActivated"])
        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        post_url = "https://www.hypixel.net"
        desc = "Activated at " + created_at
        em = discord.Embed(title="Booster info",
                           colour=discord.Colour(value=colour),
                           url=post_url,
                           description=desc)
        em.add_field(name="Game", value=s["game"])
        em.add_field(name="Purchaser", value=str(s["purchaser"]))
        em.add_field(name="Remaining time", value=s["remaining"])
        em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(s["purchaser"]))
        if not message:
            message =\
                await ctx.send(embed=em)
            await message.add_reaction("⬅")
            await message.add_reaction("❌")
            await message.add_reaction("➡")
        else:
            await message.edit(embed=em)

        def react_check(reaction, user):
            return user == ctx.author \
                and str(reaction.emoji) in ["➡", "⬅", "❌"]

        react, _ = await ctx.bot.wait_for(
            "reaction_add", timeout=timeout, check=react_check
        )
        if react is None:
            await message.remove_reaction("⬅", ctx.guild.me)
            await message.remove_reaction("❌", ctx.guild.me)
            await message.remove_reaction("➡", ctx.guild.me)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.emoji]
        if react == "next":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("➡", ctx.author)
                except discord.NotFound:
                    pass
            if page == len(booster_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.booster_menu(ctx, booster_list, message=message,
                                           page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("⬅", ctx.author)
                except discord.NotFound:
                    pass
            if page == 0:
                next_page = len(booster_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.booster_menu(ctx, booster_list, message=message,
                                           page=next_page, timeout=timeout)
        else:
            return await\
                message.delete()

    async def friends_menu(self, ctx, friends_list: list,
                           message: discord.Message=None,
                           page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        s = friends_list[page]
        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                     for x in range(6)])
        colour = int(colour, 16)
        created_at = dt.utcfromtimestamp(s["time"])
        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        post_url = "https://www.hypixel.net"
        em = discord.Embed(title="Friends",
                           colour=discord.Colour(value=colour),
                           url=post_url)
        em.add_field(name="Name", value=s["name"])
        em.add_field(name="Friend", value=str(s["fname"]))
        em.add_field(name="Since", value=created_at, inline=False)
        em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(s["fname"]))
        if not message:
            message =\
                await ctx.send(ctx.message.channel, embed=em)
            await message.add_reaction("⬅")
            await message.add_reaction("❌")
            await message.add_reaction("➡")
        else:
            message = await message.edit(embed=em)

        def react_check(reaction, user):
            return user == ctx.author \
                and str(reaction.emoji) in ["➡", "⬅", "❌"]

        react, _ = await ctx.bot.wait_for(
            "reaction_add", timeout=timeout, check=react_check
        )
        if react is None:
            await message.remove_reaction("⬅", ctx.guild.me)
            await message.remove_reaction("❌", ctx.guild.me)
            await message.remove_reaction("➡", ctx.guild.me)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.emoji]
        if react == "next":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("➡", ctx.author)
                except discord.NotFound:
                    pass
            if page == len(friends_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.friends_menu(ctx, friends_list, message=message,
                                           page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("⬅", ctx.author)
                except discord.NotFound:
                    pass
            if page == 0:
                next_page = len(friends_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.friends_menu(ctx, friends_list, message=message,
                                           page=next_page, timeout=timeout)
        else:
            return await\
                message.delete()

    def no_apikey(self):
        return "No api key available! Use `[p]hpset apikey` to set one!"

    @commands.command()
    async def hpbooster(self, ctx, *game: str):
        """
        Get active boosters. A game can be specified, in which case only the
        active booster for that game will be shown
        """
        data = {}
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(self.no_apikey())
        url = "https://api.hypixel.net/boosters?key=" + api_key
        data = await self.get_json(url)

        message = ""
        if data["success"]:
            booster_list = data["boosters"]
            if not game:
                modified_list = []
                l = [i for i in booster_list if i["length"] < i["originalLength"]]
                for item in l:
                    game_name = ""
                    remaining = \
                        str(datetime.timedelta(seconds=item["length"]))
                    name_url = "https://api.mojang.com/user/profiles/" \
                        + item["purchaserUuid"] + "/names"
                    name_data = await self.get_json(name_url)
                    name = name_data[-1]["name"]
                    for game in self.games:
                        if item["gameType"] == game["id"]:
                            game_name = game["name"]
                            break
                    cur_item = {
                        "dateActivated": item["dateActivated"]/1000,
                        "game": game_name,
                        "purchaser": name,
                        "remaining": item["length"]
                    }
                    modified_list.append(cur_item)
                await self.booster_menu(ctx, modified_list, page=0, timeout=30)

            else:
                game_n = " ".join(game)
                game_name = game_n.lower().strip()
                gameType = None
                for game in self.games:
                    if game_name == game["name"].lower():
                        game_name = game["name"]
                        gameType = game["id"]
                        break
                for item in booster_list:
                    if item["length"] < item["originalLength"] and \
                            item["gameType"] == gameType:
                        remaining = \
                           str(datetime.timedelta(seconds=item["length"]))
                        name_get_url = \
                            "https://api.mojang.com/user/profiles/" + \
                            item["purchaserUuid"] + "/names"

                        name_data = await self.get_json(name_get_url)
                        name = name_data[-1]["name"]
                        colour =\
                            ''.join([randchoice('0123456789ABCDEF')
                                     for x in range(6)])
                        colour = int(colour, 16)
                        created_at = dt.utcfromtimestamp(item["dateActivated"]/1000)
                        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
                        post_url = "https://www.hypixel.net"
                        desc = "Activated at " + created_at
                        em = discord.Embed(title="Booster info",
                                           colour=discord.Colour(value=colour),
                                           url=post_url,
                                           description=desc)
                        em.add_field(name="Game", value=game_name)
                        em.add_field(name="Purchaser", value=name)
                        em.add_field(name="Remaining time", value=item["length"])
                        em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(name))
                        await ctx.send(ctx.message.channel, embed=em)
        else:
            message = "An error occurred in getting the data"
            await ctx.send('```{}```'.format(message))

    @commands.command()
    async def hpplayer(self, ctx, name):
        """Gets data about the specified player"""

        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(self.no_apikey())
        message = ""
        url = "https://api.hypixel.net/player?key=" + \
            api_key + "&name=" + name

        data = await self.get_json(url)
        if data["success"]:
            player_data = data["player"]
            title = "Player data for " + name + ""
            colour =\
                ''.join([randchoice('0123456789ABCDEF')
                         for x in range(6)])
            colour = int(colour, 16)
            em = discord.Embed(title=title,
                               colour=discord.Colour(value=colour),
                               url="https://hypixel.net/player/{}".format(name),
                               description="Retrieved at {} UTC".format(dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
            if "buildTeam" in player_data:
                if player_data["buildTeam"] is True:
                    rank = "Build Team"
            elif "rank" in player_data:
                if player_data["rank"] == "ADMIN":
                    rank = "Admin"
                elif player_data["rank"] == "MODERATOR":
                    rank = "Moderator"
                elif player_data["rank"] == "HELPER":
                    rank = "Helper"
                elif player_data["rank"] == "YOUTUBER":
                    rank = "Youtuber"
            elif "newPackageRank" in player_data:
                if player_data["newPackageRank"] == "MVP_PLUS":
                    rank = "MVP+"
                elif player_data["newPackageRank"] == "MVP":
                    rank = "MVP"
                elif player_data["newPackageRank"] == "VIP_PLUS":
                    rank = "VIP+"
                elif player_data["newPackageRank"] == "VIP":
                    rank = "VIP"
            elif "packageRank" in player_data:
                if player_data["packageRank"] == "MVP_PLUS":
                    rank = "MVP+"
                elif player_data["packageRank"] == "MVP":
                    rank = "MVP"
                elif player_data["packageRank"] == "VIP_PLUS":
                    rank = "VIP+"
                elif player_data["packageRank"] == "VIP":
                    rank = "VIP"
            elif bool(player_data):
                rank = "None"
            else:
                message = "That player has never logged into Hypixel"
                await ctx.send('```{}```'.format(message))
                return
            em.add_field(name="Rank", value=rank)
            if "networkLevel" in player_data:
                level = str(player_data["networkLevel"])
                em.add_field(name="Level", value=level)
            else:
                level = "1"
                em.add_field(name="Level", value=level)
            if "vanityTokens" in player_data:
                tokens = str(player_data["vanityTokens"])
                em.add_field(name="Credits", value=tokens)
            first_login = self.get_time(player_data["firstLogin"])
            em.add_field(name="First login", value=first_login, inline=False)
            last_login = self.get_time(player_data["lastLogin"])
            em.add_field(name="Last login", value=last_login, inline=False)
            em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(name))
            await ctx.send(ctx.message.channel, embed=em)
        else:
            message = "An error occurred in getting the data."
            await ctx.send('```{}```'.format(message))

    @commands.command()
    async def hpfriends(self, ctx, player_name: str):
        """Gets friends for the specified player"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(self.no_apikey())
        uuid_json = await self.get_json(
            "https://api.mojang.com/users/profiles/minecraft/{}".format(
                player_name
            )
        )

        friends_json = await self.get_json("https://api.hypixel.net/friends?key={}&uuid={}".format(
            api_key,
            uuid_json["id"]
        ))
        friends_list = []
        if friends_json["success"]:
            for item in friends_json["records"]:
                if item["uuidSender"] == uuid_json["id"]:
                    name_url = "https://api.mojang.com/user/profiles/" \
                        + item["uuidReceiver"] + "/names"
                    name_data = await self.get_json(name_url)
                else:
                    name_url = "https://api.mojang.com/user/profiles/" \
                        + item["uuidSender"] + "/names"
                    name_data = await self.get_json(name_url)
                friend_name = name_data[-1]["name"]
                cur_friend = {
                    "name": player_name,
                    "fname": friend_name,
                    "time": item["started"]/1000
                }
                friends_list.append(cur_friend)
            await self.friends_menu(ctx, friends_list, message=None, page=0)

    @commands.command()
    async def hpguild(self, ctx, player_name: str):
        """Gets guild info based on the specified player"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(self.no_apikey())
        uuid_json = await self.get_json(
            "https://api.mojang.com/users/profiles/minecraft/{}".format(
                player_name
            )
        )
        guild_find_url =\
            "https://api.hypixel.net/findGuild?key={}&byUuid={}".format(
                api_key,
                uuid_json["id"]
            )
        guild_find_json = await self.get_json(guild_find_url)
        if not guild_find_json["guild"]:
            await ctx.send("The specified player does not appear to "
                               "be in a guild")
            return
        guild_id = guild_find_json["guild"]
        guild_get_url = "https://api.hypixel.net/guild?key={}&id={}".format(
            api_key,
            guild_id
        )
        guild = await self.get_json(guild_get_url)
        guild = guild["guild"]
        guildmaster_uuid = [m for m in guild["members"] if m["rank"] == "GUILDMASTER"][0]["uuid"]
        guildmaster_lookup = await self.get_json("https://api.mojang.com/user/profiles/{}/names".format(guildmaster_uuid))
        guildmaster = guildmaster_lookup[-1]["name"]
        guildmaster_face = "http://minotar.net/avatar/{}/128.png".format(guildmaster)
        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                     for x in range(6)])
        colour = int(colour, 16)
        em = discord.Embed(title=guild["name"],
                           colour=discord.Colour(value=colour),
                           url="https://hypixel.net/player/{}".format(player_name),
                           description="Created at {} UTC".format(dt.utcfromtimestamp(guild["created"]/1000).strftime("%Y-%m-%d %H:%M:%S")))
        em.add_field(name="Guildmaster", value=guildmaster, inline=False)
        em.add_field(name="Guild coins", value=guild["coins"])
        em.add_field(name="Member count", value=str(len(guild["members"])))
        em.add_field(name="Officer count", value=str(len([m for m in guild["members"] if m["rank"] == "OFFICER"])))
        em.set_thumbnail(url=guildmaster_face)

        await ctx.send(ctx.message.channel, embed=em)

    @commands.command()
    async def hpsession(self, ctx, player_name: str):
        """Shows player session status"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(self.no_apikey())
        uuid_url = "https://api.mojang.com/users/profiles/minecraft/{}".format(player_name)
        uuid = await self.get_json(uuid_url)
        uuid = uuid["id"]
        session_url = "https://api.hypixel.net/session?key={}&uuid={}".format(api_key, uuid)
        session_json = await self.get_json(session_url)
        if session_json["session"]:
            await\
                ctx.send(
                    "{} is online in {}. There are {} players there".format(
                        player_name,
                        session_json["session"]["server"],
                        str(len(session_json["session"]["players"]))
                    )
                )
        else:
            await ctx.send("That player does not appear to be online!")

    @commands.command()
    async def hpachievements(self, ctx, player, *, game):
        """Display achievements for the specified player and game"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(self.no_apikey())
        url = "https://api.hypixel.net/player?key=" + \
            api_key + "&name=" + player
        data = await self.get_json(url)
        points = 0
        achievement_count = 0
        if data["success"]:
            onetime = [item for item in data["player"]["achievementsOneTime"] if item.startswith(game)]
            tiered = [item for item in list(data["player"]["achievements"].keys()) if item.startswith(game)]
            if len(onetime) == 0 and len(tiered) == 0:
                await ctx.send("That player hasn't completed any achievements for that game!")
                return
            for item in onetime:
                achvmt_name = item[item.find("_")+1:]
                achvmt = self.achievements["achievements"][game.lower()]["one_time"][achvmt_name.upper()]
                points += achvmt["points"]
                achievement_count += 1
            for item in tiered:
                achvmt_name = item[item.find("_")+1:]
                achvmt = self.achievements["achievements"][game.lower()]["tiered"][achvmt_name.upper()]
                have_ach = False
                for tier in achvmt:
                    if data["player"]["achievements"][item] > tier["amount"]:
                        points += tier["points"]
                        have_ach = True
                if have_ach:
                    achievement_count += 1
            await ctx.send("{} has completed {} achievements worth {} points in {}".format(player, achievement_count, points, game))

    @commands.group()
    @checks.is_owner()
    async def hpset(self, ctx):
        """Settings for Hypixel cog"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx)

    @hpset.command()
    @checks.is_owner()
    async def apikey(self, ctx, key: str):
        """Sets the Hypixel API key - owner only"""
        await self.settings.api_key.set(key)
        await ctx.send('API key set!')
    
    async def achievements_getter(self):
        async with self.session.get("https://raw.githubusercontent.com/HypixelDev/PublicAPI/master/Documentation/misc/Achievements.json") as achievements_get:
            achievements = json.loads(await achievements_get.text())
        with aiofiles.open(os.path.join(data_manager.cog_data_path(self), "achievements.json"), "w") as f:
            await f.write(json.dumps(achievements, indent=4))
