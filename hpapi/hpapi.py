"""Extension for Red-DiscordBot"""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, Literal

import discord
from aiopixel import PixelClient
from aiopixel.exceptions import GuildNotFound, PlayerNotInGuild, PlayerNotFound, NoStatusForPlayer
from aiopixel.gametypes import GameType
from aiopixel.utils import get_player_uuid
from redbot.core import commands
from redbot.core import Config, commands, checks, data_manager
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils.embed import randomize_colour
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .helpers import get_booster_embed, get_friend_embed, get_guild_embed, get_player_embed


RequesterTypes = Literal["discord_deleted_user", "owner", "user", "user_strict"]

_ = Translator("Hpapi", __file__)

log = logging.getLogger("palmtree5.cogs.hpapi")


class Hpapi(commands.Cog):
    """Cog for getting info from Hypixel's API"""

    default_global = {"api_key": "", "known_guilds": []}

    default_channel = {"guild_id": "", "message": 0}

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_global(**self.default_global)
        self.settings.register_channel(**self.default_channel)
        loop = asyncio.get_event_loop()
        self.api_client = None
        self.guild_update_task = loop.create_task(self.update_guilds())
        loop.create_task(self.check_api_key())

    def cog_unload(self):
        self.guild_update_task.cancel()

    async def __error(self, ctx: commands.Context, error):
        await ctx.send("`Error in {0.command.qualified_name}: {1}`".format(ctx, error))
    
    async def red_get_data_for_user(self, *, user_id: int) -> Dict[str, Any]:
        # Cog does not store end user data
        return {}

    async def red_delete_data_for_user(self, *, requester: RequesterTypes, user_id: int) -> None:
        # Cog does not store end user data
        pass

    # Section: Load and update

    async def check_api_key(self):
        api_key = await self.settings.api_key()
        base_cmd = self.bot.get_command("hypixel")
        guild_track_cmd = self.bot.get_command("hpset guild")
        if not api_key:  # No API key, so disable the base command
            base_cmd.enabled = False
            guild_track_cmd.enabled = False
        else:
            self.api_client = PixelClient(api_key)
            base_cmd.enabled = True
            guild_track_cmd.enabled = True

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
            if self.api_client is not None:
                async with self.settings.known_guilds() as known_guilds:
                    tmp = known_guilds
                    for g in tmp:
                        known_guilds.remove(g)
                        try:
                            guild = await self.api_client.guild(g["id"])
                        except GuildNotFound:
                            data = g
                        else:
                            data = {"id": guild.id, "members": [x.uuid for x in guild.members]}
                        known_guilds.append(data)
                        await asyncio.sleep(
                            1
                        )  # allow 1 request per second, to avoid hitting the ratelimit
            com.enabled = True  # Done, so reenable the commands
            guild_track_cmd.enabled = True
            log.info("Weekly log update complete")
            await asyncio.sleep(timedelta(weeks=1).total_seconds())  # update once per week

    async def update_tracked(self):
        pass

    # End Section: Load and update

    @commands.group()
    @checks.mod_or_permissions(manage_channels=True)
    async def hpset(self, ctx: commands.Context):
        """Settings for Hypixel cog"""
        pass

    @hpset.command(name="guild")
    async def hpset_guild(
        self, ctx: commands.Context, player_name: str, channel: discord.TextChannel
    ):
        """Sets the guild to track in the specified channel"""
        if not self.api_client:
            await ctx.send(
                _("No api key available! Use `{}` to set one!").format("[p]hpset apikey")
            )
            return
        add_to_known = False
        uuid = await get_player_uuid(player_name, self.api_client._session)
        if uuid is None:
            return await ctx.send(_("It doesn't seem like there is a player with that name."))
        for g in await self.settings.known_guilds():
            if uuid in g["members"]:
                guild_id = g["id"]
                break
        else:
            try:
                guild_id = await self.api_client.find_guild_by_uuid(uuid)
            except PlayerNotInGuild:
                await ctx.send("The specified player does not appear to " "be in a guild")
                return
            else:
                add_to_known = True
        guild = await self.api_client.guild(guild_id)
        em = await get_guild_embed(guild)
        em = randomize_colour(em)
        msg = await ctx.send(embed=em)
        if add_to_known:  # add to list of known guilds to cut lookups.
            data_to_add = {"id": guild_id, "members": [x.uuid for x in guild.members]}
            async with self.settings.known_guilds() as known:
                known.append(data_to_add)
        await self.settings.channel(channel).guild_id.set(guild_id)
        await self.settings.channel(channel).message.set(msg.id)

    @hpset.command()
    @checks.is_owner()
    async def apikey(self, ctx: commands.Context, key: str):
        """Sets the Hypixel API key - owner only

        Get this by logging onto Hypixel 
        (mc.hypixel.net in MC 1.8-1.12.2) 
        and doing /api"""
        await self.settings.api_key.set(key)
        await ctx.send(_("API key set!"))
        await self.check_api_key()
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send(
                _(
                    "I tried to remove the command message for security reasons "
                    "but I don't have the necessary permissions to do so!"
                )
            )

    @commands.group(name="hypixel", aliases=["hp"])
    async def hp(self, ctx: commands.Context):
        """Base command for getting info from Hypixel's API
        
        Note that this command and all subcommands will be disabled 
        if a guild member list update is running in order to finish 
        that process more quickly"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @hp.command()
    async def currentboosters(self, ctx: commands.Context):
        """List all active boosters on the network"""
        if not self.api_client:
            await ctx.send(
                _("No api key available! Use `{}` to set one!").format("[p]hpset apikey")
            )
            return
        boosters = await self.api_client.boosters()
        pages = []
        for booster in boosters:
            if booster.length == booster.original_length:
                continue
            embed = await get_booster_embed(booster)
            embed = randomize_colour(embed)
            pages.append(embed)
        if pages:
            await menu(ctx, pages, DEFAULT_CONTROLS)
        else:
            await ctx.send(_("An error occurred in getting the data"))

    @hp.command()
    async def gamebooster(self, ctx: commands.Context, *, game: str = None):
        """
        Get the active booster for the specified game.
        """
        if not self.api_client:
            await ctx.send(
                _("No api key available! Use `{}` to set one!").format("[p]hpset apikey")
            )
            return
        game_type = GameType.from_clean_name(game)
        boosters = await self.api_client.boosters()

        game_booster = discord.utils.find(
            lambda x: x.length < x.original_length and x.game_type == game_type, boosters
        )
        if game_booster:
            embed = await get_booster_embed(game_booster)
            embed = randomize_colour(embed)
            await ctx.send(embed=embed)
        else:
            await ctx.send(_("There doesn't appear to be an active booster for that game!"))

    @hp.command(name="player")
    async def hpplayer(self, ctx: commands.Context, name: str):
        """Show info for the specified player"""
        if self.api_client is None:
            await ctx.send(
                _("No api key available! Use `{}` to set one!").format("[p]hpset apikey")
            )
            return

        try:
            player = await self.api_client.player_from_name(name)
        except PlayerNotFound:
            await ctx.send(_("That player does not exist!"))
            return
        em = await get_player_embed(player)
        em = randomize_colour(em)
        await ctx.send(embed=em)

    @hp.command(name="friends")
    async def hpfriends(self, ctx, player_name: str):
        """List friends for the specified player"""
        if not self.api_client:
            await ctx.send(
                _("No api key available! Use `{}` to set one!").format("[p]hpset apikey")
            )
            return
        player_uuid = await get_player_uuid(player_name, self.api_client._session)
        if player_uuid is None:
            return await ctx.send(_("It doesn't seem like there is a player with that name."))
        friends = await self.api_client.friends(player_uuid)
        pages = []
        msg = await ctx.send(
            "Looking up friends for {}. This may take a while if the user has "
            "a lot of users on their friends list".format(player_name)
        )
        async with ctx.channel.typing():
            # gives some indication that the command is working, because
            # this could take some time if the specified player has a lot
            # of users friended on the server
            for friend in friends:
                em = await get_friend_embed(friend)
                pages.append(em)
                await asyncio.sleep(1)
        await msg.delete()
        if pages:
            await menu(ctx, pages, DEFAULT_CONTROLS)
        else:
            await ctx.send(_("That player doesn't appear to have any friends"))

    @hp.command(name="guild")
    async def hpguild(self, ctx, player_name: str):
        """Gets guild info based on the specified player"""
        if not self.api_client:
            await ctx.send(
                _("No api key available! Use `{}` to set one!").format("[p]hpset apikey")
            )
            return
        add_to_known = False
        uuid = await get_player_uuid(player_name, session=self.api_client._session)
        if uuid is None:
            return await ctx.send(_("It doesn't seem like there is a player with that name."))
        for g in await self.settings.known_guilds():
            if uuid in g["members"]:
                guild_id = g["id"]
                break
        else:
            try:
                guild_id = await self.api_client.find_guild_by_uuid(uuid)
            except PlayerNotInGuild:
                await ctx.send(_("The specified player does not appear to " "be in a guild"))
                return
            else:
                add_to_known = True
        guild = await self.api_client.guild(guild_id)
        em = await get_guild_embed(guild)
        em = randomize_colour(em)
        await ctx.send(embed=em)
        if add_to_known:  # add to list of known guilds to cut lookups.
            data_to_add = {"id": guild_id, "members": [x.uuid for x in guild.members]}
            async with self.settings.known_guilds() as known:
                known.append(data_to_add)

    @hp.command(name="session")
    async def hpsession(self, ctx, player_name: str):
        """Shows player session status"""
        if not self.api_client:
            await ctx.send(
                _("No api key available! Use `{}` to set one!").format("[p]hpset apikey")
            )
        uuid = await get_player_uuid(player_name, session=self.api_client._session)
        if uuid is None:
            return await ctx.send(_("It doesn't seem like there is a player with that name."))
        try:
            session = await self.api_client.status(uuid)
        except NoStatusForPlayer:
            await ctx.send(_("That player does not appear to have a session!"))
        else:
            await ctx.send(
                _("{} is online in {}. There are {} players there").format(
                    player_name, session.server, len(session.players)
                )
            )
