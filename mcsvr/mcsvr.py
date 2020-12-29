import asyncio
import logging
from datetime import datetime
from functools import partial
from typing import Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from mcstatus import MinecraftServer
from mcstatus.pinger import PingResponse

from .helpers import check_server, get_server_embed, is_valid_ip, get_server_string

log = logging.getLogger("red.mcsvr")

_ = Translator("Mcsvr", __file__)


class Mcsvr(commands.Cog):
    """
    Get info about a Minecraft server.

    This only supports Java edition servers at this time.

    Also available is a server tracker that allows displaying a server and
    automatically updating its information while the cog is loaded."""

    default_channel = {"server_ip": "", "original_topic": "", "servers": []}

    default_guild = {"tracker_mode": "text"}

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=59595922, force_registration=True)
        self._svr_cache = {}
        self.config.register_channel(**self.default_channel)
        self.config.register_guild(**self.default_guild)
        self.svr_chk_task = self.bot.loop.create_task(self.server_check_loop())

    def cog_unload(self):
        self.svr_chk_task.cancel()

    @commands.command()
    async def mcserver(self, ctx: commands.Context, server_ip: str):
        """
        Display info about the specified server
        """
        if not is_valid_ip(server_ip):
            await ctx.send(
                "That is not a valid server IP! The IP must be in the form "
                "of either `0.0.0.0:25565` or `example.com:25565` (note, the "
                "port is optional but if specified, it must be in the range "
                "of 0-65535). Please check what you entered."
            )
            return
        if not self.server_ip_in_cache(server_ip, ctx.message.created_at.timestamp()):
            svr = await self.check_server(server_ip)
            if isinstance(svr, (str, Exception)):  # An error occurred, send that and stop
                return await ctx.send(f"An error occured. Message: {svr}")
            self._svr_cache[server_ip] = {
                "resp": svr,
                "invalid_at": ctx.message.created_at.timestamp() + 180,
            }
        else:
            svr = self._svr_cache[server_ip]["resp"]
        resp = get_server_embed(svr, server_ip)
        await ctx.send(embed=resp)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def addserver(
        self, ctx: commands.Context, server_ip: str, channel: discord.TextChannel = None
    ):
        """
        Set a server to track.

        The server info will be used for the channel's description.
        """
        if not channel:
            channel = ctx.channel

        tracker_mode = await self.config.guild(ctx.guild).tracker_mode()
        if tracker_mode == "text" and not channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(_("I do not have permissions to manage channels!"))
            return
        if is_valid_ip(server_ip):
            if not self.server_ip_in_cache(server_ip, ctx.message.created_at.timestamp()):
                svr = await self.check_server(server_ip)
                if isinstance(svr, (str, Exception)):  # An error occurred, send that and stop
                    return await ctx.send(f"An error occured. Message: {svr}")
                self._svr_cache[server_ip] = {
                    "resp": svr,
                    "invalid_at": ctx.message.created_at.timestamp() + 180,
                }
            else:
                svr = self._svr_cache[server_ip]["resp"]
            if tracker_mode == "text":
                current_ip = await self.config.channel(channel).server_ip()
                if current_ip:
                    await ctx.send(_("A server is already set up in this channel!"))
                    return
                resp = get_server_string(svr, server_ip)
                await self.config.channel(channel).server_ip.set(server_ip)
                await self.config.channel(channel).original_topic.set(channel.topic)
                await channel.edit(topic=resp)
                await ctx.tick()
            else:
                current_server_list = await self.config.channel(channel).servers()
                for server in current_server_list:
                    if server["server_ip"] == server_ip:
                        await ctx.send(_("This server is already being tracked in this channel!"))
                        return
                resp = get_server_embed(svr, server_ip)
                msg = await channel.send(embed=resp)

                current_server_list.append({"server_ip": server_ip, "message": msg.id})
                await self.config.channel(channel).servers.set(current_server_list)
        else:
            await ctx.send(_("That is not a valid server IP!"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def delserver(
        self, ctx: commands.Context, server_ip: str = None, channel: discord.TextChannel = None
    ):
        """
        Removes a server from the tracker
        """
        if channel is None:
            channel = ctx.channel
        tracker_mode = await self.config.guild(ctx.guild).tracker_mode()
        if tracker_mode == "text":
            await self.config.channel(channel).server_ip.set("")
            orig_topic = await self.config.channel(channel).original_topic()
            await channel.edit(topic=orig_topic)
            await self.config.channel(channel).original_topic.set("")
            await ctx.tick()
        else:
            if server_ip is None:
                await ctx.send("Tracker is in embed mode but no server was passed to remove!")
                return
            servers = await self.config.channel(channel).servers()
            for server in servers:
                if server["server_ip"] == server_ip:
                    to_remove = server
                    break
            else:
                await ctx.send("I was not tracking that server!")
                return
            msg = await channel.fetch_message(to_remove["message"])
            await msg.delete()
            servers.remove(to_remove)
            await self.config.channel(channel).servers.set(servers)
            await ctx.tick()

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def mcset(self, ctx: commands.Context):
        """
        Settings for the server tracker
        """
        pass

    @mcset.command(name="mode")
    async def mcset_mode(self, ctx: commands.Context, mode: str, confirm: bool = False):
        """
        Sets the server tracker mode for the guild.

        Valid values for the mode param are `text` or `embed`.
        If set to embed, multiple servers can be tracked in one channel.
        If set to text, only one server is allowed per channel because
        the channel topic will be used for the display.
        """
        if mode not in ("text", "embed"):
            await ctx.send(
                _("Invalid value for `{}`. Valid values are `{}`, `{}`").format(
                    "mode", "text", "embed"
                )
            )
            return
        current_mode = await self.config.guild(ctx.guild).tracker_mode()
        if current_mode != mode:
            if not confirm:
                await ctx.send(
                    _(
                        "This will remove all currently tracked servers! "
                        "To confirm this is what you want to do, type {}"
                    ).format("`{}mcset mode {} yes`".format(ctx.prefix, mode))
                )
                return
            await self.do_mode_toggle_cleanup(current_mode, ctx.guild)
            await self.config.guild(ctx.guild).tracker_mode.set(mode)
            await ctx.tick()
        else:
            await ctx.send(_("I was already in mode `{}`").format(mode))
    
    async def check_server(self, addr: str) -> Union[PingResponse, str, None]:
        server = MinecraftServer.lookup(addr)

        try:
            status = await server.async_status()
        except Exception as e:
            return e
        return status

    def server_ip_in_cache(self, server_ip: str, time: float):
        if server_ip not in self._svr_cache:
            return False
        server = self._svr_cache[server_ip]
        if server["invalid_at"] <= time:
            del self._svr_cache[server_ip]
            return False
        return True

    async def do_mode_toggle_cleanup(self, mode, guild: discord.Guild):
        if mode == "text":
            for channel in guild.text_channels:
                current_server = await self.config.channel(channel).server_ip()
                if current_server:
                    topic = await self.config.channel(channel).original_topic()
                    await channel.edit(topic=topic)
                    await self.config.channel(channel).server_ip.set("")
                    await self.config.channel(channel).original_topic.set("")
        else:
            for channel in guild.text_channels:
                servers = await self.config.channel(channel).servers()
                for server in servers:
                    msg = await channel.fetch_message(server["message"])
                    await msg.delete()
                await self.config.channel(channel).servers.set([])

    async def server_check_loop(self):
        check_time = 300
        while self == self.bot.get_cog("Mcsvr"):
            log.debug("Starting server checks")
            all_channels = await self.config.all_channels()
            for channel_id, info in all_channels.items():
                now = datetime.utcnow().timestamp()
                channel = self.bot.get_channel(channel_id)
                cur_mode = await self.config.guild(channel.guild).tracker_mode()
                if channel is None or (
                    cur_mode == "text"
                    and not channel.permissions_for(channel.guild.me).manage_channels
                ):
                    continue

                if cur_mode == "text":
                    server_ip = info["server_ip"]
                    if not server_ip:
                        continue
                    if not self.server_ip_in_cache(server_ip, now):
                        svr = await self.check_server(server_ip)
                        if isinstance(svr, (str, Exception)):
                            continue
                        self._svr_cache[server_ip] = {"resp": svr, "invalid_at": now + 180}
                    else:
                        svr = self._svr_cache[server_ip]["resp"]
                    resp = get_server_string(svr, server_ip)
                    await channel.edit(topic=resp)
                else:
                    for server in info["servers"]:
                        server_ip = server["server_ip"]
                        message = await channel.fetch_message(server["message"])
                        if message is None:
                            continue
                        if not self.server_ip_in_cache(server_ip, now):
                            svr = await self.check_server(server_ip)
                            if isinstance(svr, (str, Exception)):
                                continue
                            self._svr_cache[server_ip] = {"resp": svr, "invalid_at": now + 180}
                        else:
                            svr = self._svr_cache[server_ip]["resp"]
                        await message.edit(embed=get_server_embed(svr, server_ip))

            now = datetime.utcnow()
            next_check = datetime.utcfromtimestamp(now.timestamp() + check_time)
            log.debug("Done. Next check at {}".format(next_check.strftime("%Y-%m-%d %H:%M:%S")))
            await asyncio.sleep(check_time)
