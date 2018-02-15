"""Extension for Red-DiscordBot"""
import asyncio
import datetime
import json
import logging
from datetime import datetime as dt, timedelta

import aiofiles
import aiohttp
import discord
from discord.ext import commands
from redbot.core import Config, RedContext, checks, data_manager
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.core.utils.embed import randomize_colour

from .errors import NoAPIKeyException
from .helpers import get_network_level, get_rank, get_achievement_points, count_quest_completions
from .menus import booster_menu, friends_menu

_ = CogI18n("Hpapi", __file__)

log = logging.getLogger("red.hpapi")


class Hpapi:
    """Cog for getting info from Hypixel's API"""
    default_global = {
        "api_key": "",
        "known_guilds": []
    }

    default_channel = {
        "guild_id": "",
        "message": 0
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(
            self, identifier=59595922, force_registration=True
        )
        self.settings.register_global(**self.default_global)
        self.settings.register_channel(**self.default_channel)
        self.session = aiohttp.ClientSession()
        loop = asyncio.get_event_loop()
        self.guild_update_task = loop.create_task(self.update_guilds())
        loop.create_task(self.achievements_getter())
        loop.create_task(self.check_api_key())
        self.achievements = None
        self.games = None
        loop.create_task(self.load_games())

    def __unload(self):
        self.session.close()
        self.guild_update_task.cancel()

    async def __error(self, ctx: RedContext, error):
        await ctx.send("`Error in {0.command.qualified_name}: {1}`".format(ctx, error))

    # Section: Load and update
    async def load_achievements(self):
        achieve_file = data_manager.cog_data_path(self) / "achievements.json"
        async with aiofiles.open(str(achieve_file)) as f:
            self.achievements = json.loads(await f.read())

    async def load_games(self):
        async with aiofiles.open(str(data_manager.bundled_data_path(self) / "games.json")) as f:
            self.games = json.loads(await f.read())

    async def check_api_key(self):
        api_key = await self.settings.api_key()
        if not api_key:  # No API key, so disable the base command
            base_cmd = self.bot.get_command("hypixel")
            base_cmd.enabled = False
            guild_track_cmd = self.bot.get_command("hpset guild")
            guild_track_cmd.enabled = False

    async def update_guilds(self):
        """Updates the guild members for the list of known guilds.
        This may take a while if there are a lot of them.

        Note that [p]hypixel and all of its subcommands are disabled 
        while the update is in progress. This is to ensure that new additions 
        are not made while the update is in progress and to ensure this 
        function has exclusive use of the api key during the update process"""
        while self == self.bot.get_cog("Hpapi"):
            com = self.bot.get_command("hypixel")
            com.enabled = False  # disable the commands while this is in progress
            guild_track_cmd = self.bot.get_command("hpset guild")
            guild_track_cmd.enabled = False
            log.info("Starting weekly guild update")
            api_key = await self.settings.api_key()
            if api_key:  # no sense in even checking guilds if we don't have an API key
                async with self.settings.known_guilds() as known_guilds:
                    tmp = known_guilds
                    for g in tmp:
                        known_guilds.remove(g)

                        guild_get_url = "https://api.hypixel.net/guild?key={}&id={}".format(
                            api_key,
                            g["id"]
                        )
                        guild_data = await self.get_json(guild_get_url)
                        if guild_data["success"]:
                            data = {
                                "id": g["id"],
                                "members": [x["uuid"] for x in guild_data["guild"]["members"]]
                            }
                        else:
                            data = g
                        known_guilds.append(data)
                        await asyncio.sleep(1)  # allow 1 request per second, to avoid hitting the ratelimit
            com.enabled = True  # Done, so reenable the commands
            guild_track_cmd.enabled = True
            log.info("Weekly log update complete")
            await asyncio.sleep(timedelta(weeks=1).total_seconds())  # update once per week

    async def update_tracked(self):
        pass

    async def achievements_getter(self):
        achieve_file = data_manager.cog_data_path(self) / "achievements.json"
        if achieve_file.exists():
            async with self.session.get("https://api.github.com/repos/HypixelDev/PublicAPI/contents/Documentation/misc/Achievements.json") as sha_check:
                data = await sha_check.json()
            if data["size"] != achieve_file.stat().st_size: # File on Github is not the same as the local one
                achieve_file.unlink()  # need to replace
                async with self.session.get("https://raw.githubusercontent.com/HypixelDev/PublicAPI/master/Documentation/misc/Achievements.json") as achievements_get:
                    achievements = json.loads(await achievements_get.text())
                async with aiofiles.open(str(achieve_file), "w") as f:
                    await f.write(json.dumps(achievements, separators=(',', ':')) + "\n")
        else:
            async with self.session.get("https://raw.githubusercontent.com/HypixelDev/PublicAPI/master/Documentation/misc/Achievements.json") as achievements_get:
                achievements = json.loads(await achievements_get.text())
            async with aiofiles.open(str(achieve_file), "w") as f:
                await f.write(json.dumps(achievements, separators=(',', ':')) + "\n")
        await self.load_achievements()
    
    # End Section: Load and update

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
    @checks.mod_or_permissions(manage_channel=True)
    async def hpset(self, ctx: RedContext):
        """Settings for Hypixel cog"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @hpset.command(name="guild")
    async def hpset_guild(self, ctx: RedContext, player_name: str, channel: discord.TextChannel):
        """Sets the guild to track in the specified channel"""
        api_key = await self.settings.api_key()
        if not api_key:
            raise NoAPIKeyException(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
        add_to_known = False
        uuid_json = await self.get_json(
            "https://api.mojang.com/users/profiles/minecraft/{}".format(
                player_name
            )
        )
        for g in await self.settings.known_guilds():
            if uuid_json["id"] in g["players"]:
                guild_id = g["id"]
                break
        else:
            guild_find_url = \
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
            add_to_known = True
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
                           description="Created at {} UTC".format(
                               dt.utcfromtimestamp(guild["created"] / 1000).strftime("%Y-%m-%d %H:%M:%S")))
        em = randomize_colour(em)
        em.add_field(name="Guildmaster", value=gmaster, inline=False)
        em.add_field(name="Guild coins", value=guild["coins"])
        em.add_field(name="Member count", value=str(len(guild["members"])))
        em.add_field(name="Officer count", value=str(len([m for m in guild["members"] if m["rank"] == "OFFICER"])))
        em.set_thumbnail(url=gmaster_face)

        msg = await ctx.send(embed=em)
        if add_to_known:  # add to list of known guilds to cut lookups.
            data_to_add = {
                "id": guild_id,
                "players": [x["uuid"] for x in guild["members"]]
            }
            async with self.settings.known_guilds() as known:
                known.append(data_to_add)
        await self.settings.channel(channel).guild_id.set(guild_id)
        await self.settings.channel(channel).message.set(msg.id)

    @hpset.command()
    @checks.is_owner()
    async def apikey(self, ctx: RedContext, key: str):
        """Sets the Hypixel API key - owner only

        Get this by logging onto Hypixel 
        (mc.hypixel.net in MC 1.8-1.12.2) 
        and doing /api"""
        await self.settings.api_key.set(key)
        await ctx.send(_('API key set!'))
        base_cmd = ctx.bot.get_command("hypixel")
        base_cmd.enabled = True
        guild_track_cmd = self.bot.get_command("hpset guild")
        guild_track_cmd.enabled = True
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send(
                _("I tried to remove the command message for security reasons "
                  "but I don't have the necessary permissions to do so!")
            )

    @commands.group(name="hypixel", aliases=["hp"])
    async def hp(self, ctx: RedContext):
        """Base command for getting info from Hypixel's API
        
        Note that this command and all subcommands will be disabled 
        if a guild member list update is running in order to finish 
        that process more quickly"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @hp.command()
    async def currentboosters(self, ctx: RedContext):
        """List all active boosters on the network"""
        api_key = await self.settings.api_key()
        if not api_key:
            raise NoAPIKeyException(
                _("No api key available! Use `{}` to set one!"
                 ).format("[p]hpset apikey")
            )
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
            raise NoAPIKeyException(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
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
        """Show info for the specified player"""
        api_key = await self.settings.api_key()
        if not api_key:
            raise NoAPIKeyException(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))

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

            if "mostRecentGameType" in player_data:
                for game in self.games:
                    if player_data["mostRecentGameType"] == game["type_name"]:
                        em.add_field(name="Last Playing", value=game["clean_name"])
                        break
            if self.achievements:
                log.info("Calculating achievement points...")
                achievement_points = get_achievement_points(self.achievements["achievements"], player_data)
                em.add_field(name="Achievement Points", value=str(achievement_points))
            if "quests" in player_data:
                em.add_field(name="Quests Completed", value=str(count_quest_completions(player_data)))
            if "lastLogout" in player_data and player_data["lastLogin"] > player_data["lastLogout"]:
                em.add_field(name="Online", value="Yes")
            first_login = self.get_time(player_data["firstLogin"])
            last_login = self.get_time(player_data["lastLogin"])
            em.add_field(name="First/Last login", value="{} / {}".format(first_login, last_login), inline=False)

            em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(name))
            await ctx.send(embed=em)
        else:
            await ctx.send(_("An error occurred in getting the data."))

    @hp.command(name="friends")
    async def hpfriends(self, ctx, player_name: str):
        """List friends for the specified player"""
        api_key = await self.settings.api_key()
        if not api_key:
            raise NoAPIKeyException(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
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
            raise NoAPIKeyException(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
        add_to_known = False
        uuid_json = await self.get_json(
                "https://api.mojang.com/users/profiles/minecraft/{}".format(
                    player_name
                )
            )
        for g in await self.settings.known_guilds():
            if uuid_json["id"] in g["players"]:
                guild_id = g["id"]
                break
        else:
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
            add_to_known = True
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
        if add_to_known:  # add to list of known guilds to cut lookups.
            data_to_add = {
                "id": guild_id,
                "players": [x["uuid"] for x in guild["members"]]
            }
            async with self.settings.known_guilds() as known:
                known.append(data_to_add)

    @hp.command(name="session")
    async def hpsession(self, ctx, player_name: str):
        """Shows player session status"""
        api_key = await self.settings.api_key()
        if not api_key:
            raise NoAPIKeyException(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
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
            raise NoAPIKeyException(_("No api key available! Use `{}` to set one!").format("[p]hpset apikey"))
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
