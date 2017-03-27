from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
import discord
import os
import asyncio
from mcstatus import MinecraftServer


class Mcsvr():
    """Cog for getting info about a Minecraft server"""
    def __init__(self, bot):
        self.settings_file = "data/mcsvr/mcsvr.json"
        self.settings = dataIO.load_json(self.settings_file)
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True, name="mcsvr")
    async def _mcsvr(self, ctx):
        """Commands for getting info about a Minecraft server"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_mcsvr.command(pass_context=True, no_pm=True, name="count")
    async def _count(self, ctx, server_ip: str=None):
        """Gets player count for the specified server"""
        server = ctx.message.server
        if server_ip is None:
            if server.id in self.settings and len(self.settings[server.id]) == 1:
                server_ip = self.settings[server.id][0]
            else:
                await self.bot.say("I'm not sure what server you want to check!")
                return
        mc_server = MinecraftServer.lookup(server_ip).status()
        online_count = mc_server.players.online
        max_count = mc_server.players.max
        message = "Player count for " + server_ip + ":\n\n" + \
            str(online_count) + "/" + str(max_count)
        await self.bot.say("```{}```".format(message))

    @_mcsvr.command(pass_context=True, no_pm=True, name="version")
    async def _version(self, ctx, server_ip: str=None):
        """
        Gets information about the required Minecraft
        version for the specified server
        """
        server = ctx.message.server
        if server_ip is None:
            if server.id in self.settings and len(self.settings[server.id]) == 1:
                server_ip = self.settings[server.id][0]
            else:
                await self.bot.say("I'm not sure what server you want to check!")
                return
        mc_server = MinecraftServer.lookup(server_ip).status()
        message = "Server version for " + server_ip + ":\n\n" + \
            str(mc_server.version.name)
        await self.bot.say("```{}```".format(message))

    @checks.admin_or_permissions(administrator=True)
    @commands.command(pass_context=True, no_pm=True, name="mcsvrset")
    async def _mcsvrset(self, ctx, channel: discord.Channel, server_ip: str):
        """Settings for being notified of server issues"""
        if not channel or not server_ip:
            await self.bot.say("Sorry, can't do that! Try specifying a channel and a server IP")
        else:
            chn_name = channel.name
            svr_id = ctx.message.server.id
            server_status = "down"
            if svr_id not in self.settings:
                self.settings[svr_id] = []
            try:
                mc_server = MinecraftServer.lookup(server_ip).status()
                server_status = "up"
                await self.bot.send_message(channel, "The server is up!")
            except ConnectionRefusedError:
                server_status = "down"
                await self.bot.send_message(channel, "The server is down!")
            svr_to_add = {"chn_name": chn_name, "server_ip": server_ip, "server_status": server_status}
            self.settings[svr_id].append(svr_to_add)
            dataIO.save_json(self.settings_file, self.settings)

    async def mc_servers_check(self):
        CHECK_TIME = 60
        while self == self.bot.get_cog("Mcsvr"):
            bot_servers = list(self.bot.servers)
            for server in bot_servers:
                print(server.id in self.settings)
                if server.id in self.settings:
                    for mc_svr in self.settings[server.id]:
                        channel_name = self.settings[server.id]["chn_name"]
                        server_ip = self.settings[server.id]["server_ip"]
                        server_status = self.settings[server.id]["server_status"]
                        try:
                            mc_server = MinecraftServer.lookup(server_ip).status()
                            if server_status == "down":
                                await self.bot.send_message(discord.utils.get(self.bot.get_all_channels(), server__id=server.id, name=channel_name), "The server is up again!")
                            server_status = "up"
                        except ConnectionRefusedError:
                            if server_status == "up":
                                await self.bot.send_message(discord.utils.get(self.bot.get_all_channels(), server__id=server.id, name=channel_name), "Oh no, the server went down!")
                            server_status = "down"
                        self.settings[server.id]["server_status"] = server_status
            dataIO.save_json(self.settings_file, self.settings)
            await asyncio.sleep(CHECK_TIME)


def check_folders():
    if not os.path.exists("data/mcsvr"):
        print("Creating data/mcsvr folder...")
        os.makedirs("data/mcsvr")


def check_files():
    f = "data/mcsvr/mcsvr.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty mcsvr.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    n = Mcsvr(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.mc_servers_check())
    bot.add_cog(n)
