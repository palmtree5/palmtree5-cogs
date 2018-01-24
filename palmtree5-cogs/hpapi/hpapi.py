"""Extension for Red-DiscordBot"""
import asyncio
import datetime
import json
from datetime import datetime as dt

import aiofiles
import aiohttp
import discord
from discord.ext import commands
from redbot.core import Config, checks, data_manager, RedContext
from redbot.core.i18n import CogI18n
from redbot.core.utils.embed import randomize_colour

from .helpers import get_rank, get_network_level
from .menus import friends_menu, booster_menu

_ = CogI18n("Hpapi", __file__)


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
        self.achievements = None
        self.games = None
        loop.create_task(self.load_achievements())
        loop.create_task(self.load_games())

    def __unload(self):
        self.session.close()

    async def load_achievements(self):
        async with aiofiles.open(str(data_manager.cog_data_path(self) / "achievements.json")) as f:
            self.achievements = json.loads(await f.read())

    async def load_games(self):
        async with aiofiles.open(str(data_manager.bundled_data_path(self) / "games.json")) as f:
            self.games = json.loads(await f.read())

    async def get_json(self, url):
        async with self.session.get(url) as r:
            ret = await r.json()
        return ret

    async def get_mc_uuid(self, name: str):
        url = "https://api.mojang.com/users/profiles/minecraft/{}".format(name)
        async with self.session.get(url) as r:
            if r.status == 204:  # name is not in use
                return None
            else:
                data = await r.json()
                return data["id"]

    @staticmethod
    def get_time(ms):
        time = dt.utcfromtimestamp(ms/1000)
        return time.strftime('%Y-%m-%d %H:%M:%S')
    
    @commands.group()
    @checks.is_owner()
    async def hpset(self, ctx: RedContext):
        """Settings for Hypixel cog"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @hpset.command()
    @checks.is_owner()
    async def apikey(self, ctx: RedContext, key: str):
        """Sets the Hypixel API key - owner only
        Get this by logging onto Hypixel and doing /api"""
        await self.settings.api_key.set(key)
        await ctx.send('API key set!')

    @commands.group(name="hypixel", aliases=["hp"])
    async def hp(self, ctx: RedContext):
        """Base command for getting info from Hypixel's API"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @hp.command()
    async def currentboosters(self, ctx: RedContext):
        """Get all active boosters on the network"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
            return
        url = "https://api.hypixel.net/boosters?key=" + api_key
        data = await self.get_json(url)
        if data["success"]:
            booster_list = data["boosters"]
            modified_list = []
            l = [i for i in booster_list if i["length"] < i["originalLength"]]
            for item in l:
                game_name = ""
                for game in self.games:
                    if item["gameType"] == game["id"]:
                        game_name = game["clean_name"]
                        break
                name_url = "https://api.mojang.com/user/profiles/" \
                           + item["purchaserUuid"] + "/names"
                name_data = await self.get_json(name_url)
                name = name_data[-1]["name"]
                desc = "Activated at {}".format(
                    dt.utcfromtimestamp(
                        item["dateActivated"] / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S")
                )
                thumb_url = "http://minotar.net/avatar/{}/128.png".format(
                    name
                )
                remaining = \
                    str(datetime.timedelta(seconds=item["length"]))
                fields = [
                    {
                        "name": "Game",
                        "value": game_name
                    },
                    {
                        "name": "Purchaser",
                        "value": name
                    },
                    {
                        "name": "Remaining time",
                        "value": remaining
                    }
                ]
                embed = discord.Embed(
                    title="Booster info",
                    url="https://store.hypixel.net/category/307502",
                    description=desc
                )
                for field in fields:
                    embed.add_field(**field)
                embed.set_thumbnail(url=thumb_url)
                embed = randomize_colour(embed)
                modified_list.append(embed)
            await booster_menu(ctx, modified_list, page=0, timeout=30)
        else:
            await ctx.send(_("An error occurred in getting the data"))

    @hp.command()
    async def gamebooster(self, ctx: RedContext, *, game: str=None):
        """
        Get the active booster for the specified game.
        """
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
            return
        url = "https://api.hypixel.net/boosters?key=" + api_key
        data = await self.get_json(url)

        if data["success"]:
            booster_list = data["boosters"]
            game_n = game
            game_name = game_n.lower().strip()
            for game in self.games:
                if game_name == game["clean_name"].lower() or\
                        game_name == game["db_name"].lower() or\
                        game_name == game["type_name"].lower():
                    game_name = game["clean_name"]
                    game_type = game["id"]
                    break
            else:
                await ctx.send(_("That game doesn't exist!"))
                return
            booster_list = [i for i in booster_list if i["gameType"] == game_type]
            sorted_booster_list = sorted(booster_list, key=lambda i: i["dateActivated"])
            if not sorted_booster_list:
                await ctx.send(_("No boosters active for game {}").format(game_name))
                return
            current_booster = sorted_booster_list[0]
            sorted_booster_list.remove(current_booster)
            remaining_boosters = len(sorted_booster_list)
            remaining = str(datetime.timedelta(seconds=current_booster["length"]))
            name_get_url = \
                "https://api.mojang.com/user/profiles/" + \
                current_booster["purchaserUuid"] + "/names"

            name_data = await self.get_json(name_get_url)
            name = name_data[-1]["name"]

            created_at = dt.utcfromtimestamp(current_booster["dateActivated"]/1000)
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
            desc = "Activated at " + created_at
            em = discord.Embed(title="Current booster for {}".format(game_name),
                               url="https://store.hypixel.net/category/307502",
                               description="and {} boosters remaining".format(remaining_boosters))
            em = randomize_colour(em)
            em.add_field(name="Purchaser", value=name)
            em.add_field(name="Remaining time", value=remaining)
            em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(name))
            em.set_footer(text=desc)
            await ctx.send(embed=em)
        else:
            await ctx.send(_("An error occurred in getting the data"))

    @hp.command(name="player")
    async def hpplayer(self, ctx: RedContext, name: str):
        """Gets data about the specified player"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
            return

        uuid = await self.get_mc_uuid(name)  # let's get the user's UUID
        if uuid is None:
            await ctx.send("That name does not have a UUID associated with it!")
            return

        url = "https://api.hypixel.net/player?key=" + \
            api_key + "&uuid=" + uuid

        data = await self.get_json(url)
        if data["success"]:
            player_data = data["player"]
            rank = get_rank(player_data)
            if rank is None:
                await ctx.send(_("That player has never logged into {}!").format("Hypixel"))
                return
            title = "{}{}".format("[{}] ".format(rank) if rank else "", player_data["displayname"])

            em = discord.Embed(title=title,
                               url="https://hypixel.net/player/{}".format(player_data["displayname"]),
                               description="Minecraft version: {}".format(
                                   player_data["mcVersionRp"] if "mcVersionRp" in player_data else "Unknown"
                               ))
            em = randomize_colour(em)

            em.add_field(name="Rank", value=rank if rank else "None")
            em.add_field(name="Level", value=str(get_network_level(player_data["networkExp"])))

            first_login = self.get_time(player_data["firstLogin"])
            last_login = self.get_time(player_data["lastLogin"])
            em.add_field(name="First/Last login", value="{} / {}".format(first_login, last_login), inline=False)

            em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(name))
            await ctx.send(embed=em)
        else:
            await ctx.send(_("An error occurred in getting the data."))

    @hp.command(name="friends")
    async def hpfriends(self, ctx, player_name: str):
        """Gets friends for the specified player"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
            return
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
            msg = await ctx.send(
                "Looking up friends for {}. This may take a while if the user has "
                "a lot of users on their friends list".format(player_name))
            async with ctx.channel.typing():
                # gives some indication that the command is working, because
                # this could take some time if the specified player has a lot
                # of users friended on the server
                for item in friends_json["records"]:
                    if item["uuidSender"] == uuid_json["id"]:
                        name_url = "https://api.mojang.com/user/profiles/" \
                            + item["uuidReceiver"] + "/names"
                        name_data = await self.get_json(name_url)
                    else:
                        name_url = "https://api.mojang.com/user/profiles/" \
                            + item["uuidSender"] + "/names"
                        name_data = await self.get_json(name_url)
                    friend_name = name_data[-1]["name"]  # last item in list is most recent name
                    cur_friend = {
                        "name": player_name,
                        "fname": friend_name,
                        "time": item["started"]/1000
                    }
                    friends_list.append(cur_friend)
                    await asyncio.sleep(1)
            await msg.delete()
            await friends_menu(ctx, friends_list, message=None, page=0)

    @hp.command(name="guild")
    async def hpguild(self, ctx, player_name: str):
        """Gets guild info based on the specified player"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
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
        gmaster_uuid = [m for m in guild["members"] if m["rank"] == "GUILDMASTER"][0]["uuid"]
        gmaster_lookup = await self.get_json("https://api.mojang.com/user/profiles/{}/names".format(gmaster_uuid))
        gmaster = gmaster_lookup[-1]["name"]
        gmaster_face = "http://minotar.net/avatar/{}/128.png".format(gmaster)
        em = discord.Embed(title=guild["name"],
                           url="https://hypixel.net/player/{}".format(player_name),
                           description="Created at {} UTC".format(dt.utcfromtimestamp(guild["created"]/1000).strftime("%Y-%m-%d %H:%M:%S")))
        em = randomize_colour(em)
        em.add_field(name="Guildmaster", value=gmaster, inline=False)
        em.add_field(name="Guild coins", value=guild["coins"])
        em.add_field(name="Member count", value=str(len(guild["members"])))
        em.add_field(name="Officer count", value=str(len([m for m in guild["members"] if m["rank"] == "OFFICER"])))
        em.set_thumbnail(url=gmaster_face)

        await ctx.send(embed=em)

    @hp.command(name="session")
    async def hpsession(self, ctx, player_name: str):
        """Shows player session status"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
            return
        uuid_url = "https://api.mojang.com/users/profiles/minecraft/{}".format(player_name)
        uuid = await self.get_json(uuid_url)
        uuid = uuid["id"]
        session_url = "https://api.hypixel.net/session?key={}&uuid={}".format(api_key, uuid)
        session_json = await self.get_json(session_url)
        if session_json["session"]:
            await\
                ctx.send(
                    _("{} is online in {}. There are {} players there").format(
                        player_name,
                        session_json["session"]["server"],
                        str(len(session_json["session"]["players"]))
                    )
                )
        else:
            await ctx.send(_("That player does not appear to be online!"))

    @hp.command(name="wdstats")
    async def hpwdstats(self, ctx: RedContext):
        """Displays Watchdog's stats"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
            return
        url = "https://api.hypixel.net/watchdogstats?key={}".format(api_key)
        data = await self.get_json(url)
        if not data["success"]:
            await ctx.send(_("Error! {}").format(data["cause"]))
            return
        else:
            embed = discord.Embed(title="Watchdog stats")
            embed = randomize_colour(embed)
            embed.add_field(name="Past day (Watchdog)", value=str(data["watchdog_rollingDaily"]), inline=False)
            embed.add_field(name="Past day (Staff)", value=str(data["staff_rollingDaily"]), inline=False)
            embed.add_field(name="Total (Watchdog)", value=str(data["watchdog_total"]), inline=False)
            embed.add_field(name="Total (Staff)", value=str(data["staff_total"]), inline=False)
            await ctx.send(embed=embed)

    @hp.command(name="achievements")
    async def hpachievements(self, ctx, player, *, game):
        """Display achievements for the specified player and game"""
        api_key = await self.settings.api_key()
        if not api_key:
            await ctx.send(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
            return
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
    
    async def achievements_getter(self):
        async with self.session.get("https://raw.githubusercontent.com/HypixelDev/PublicAPI/master/Documentation/misc/Achievements.json") as achievements_get:
            achievements = json.loads(await achievements_get.text())
        async with aiofiles.open(str(data_manager.cog_data_path(self) / "achievements.json"), "w") as f:
            await f.write(json.dumps(achievements, indent=4))
