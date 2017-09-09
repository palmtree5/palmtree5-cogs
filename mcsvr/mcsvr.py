import socket

from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
import discord
import os
import asyncio
from functools import partial
from mcstatus import MinecraftServer


class Mcsvr:
    """Cog for getting info about a Minecraft server"""
    def __init__(self, bot):
        self.settings_file = "data/mcsvr/mcsvr.json"
        self.settings = dataIO.load_json(self.settings_file)
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def players(self, ctx, server_ip: str=None):
        """Gets player count (and list, if query is enabled on the server)
         for the specified server"""
        server = ctx.message.server
        players = None
        if server_ip is None:
            if server.id in self.settings and len(self.settings[server.id]) == 1:
                server_ip = self.settings[server.id][0]["server_ip"]
            else:
                await self.bot.say("I'm not sure what server you want to check!")
                return
        loop = asyncio.get_event_loop()
        mc_server = await loop.run_in_executor(None, partial(self.check_server, server_ip))
        if hasattr(mc_server, "software"):  # check_server returned a QueryResponse
            players = mc_server.players.names
        online_count = mc_server.players.online
        max_count = mc_server.players.max
        message = "Player count for " + server_ip + ":\n\n" + \
            str(online_count) + "/" + str(max_count)
        if players and online_count > 0:
            message += "\nPlayers currently online:\n"
            message += ", ".join(players)
        await self.bot.say("```{}```".format(message))

    @commands.command(pass_context=True, no_pm=True)
    async def serverver(self, ctx, server_ip: str=None):
        """
        Gets information about the required Minecraft
        version for the specified server
        """
        server = ctx.message.server
        if server_ip is None:
            if server.id in self.settings and len(self.settings[server.id]) == 1:
                server_ip = self.settings[server.id][0]["server_ip"]
            else:
                await self.bot.say("I'm not sure what server you want to check!")
                return
        loop = asyncio.get_event_loop()
        mc_server = await loop.run_in_executor(None, partial(self.check_server, server_ip))
        message = "Server version for " + server_ip + ":\n\n" + \
            str(
                mc_server.software.version if hasattr(mc_server, "software")
                else mc_server.version.name
            )
        await self.bot.say("```{}```".format(message))

    @checks.admin_or_permissions(administrator=True)
    @commands.command(pass_context=True, no_pm=True)
    async def addserver(self, ctx, channel: discord.Channel, server_ip: str):
        """Add a server to the tracker"""
        if not channel or not server_ip:
            await self.bot.say("Sorry, can't do that! Try specifying a channel and a server IP")
        else:
            chn_name = channel.name
            svr_id = ctx.message.server.id
            if svr_id not in self.settings:
                self.settings[svr_id] = []
            loop = asyncio.get_event_loop()
            mc_server = await loop.run_in_executor(None, partial(self.check_server, server_ip))
            if mc_server is not None:
                emb = await self.get_server_embed(mc_server, server_ip)
                msg = await self.bot.send_message(channel, embed=emb)
            else:
                emb = await self.get_server_embed(None, server_ip)
                msg = await self.bot.send_message(channel, embed=emb)

            svr_to_add = {
                "chn_id": channel.id,
                "server_ip": server_ip,
                "server_message": msg.id
            }
            self.settings[svr_id].append(svr_to_add)
            dataIO.save_json(self.settings_file, self.settings)
            await self.bot.say("Done adding that server!")

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(administrator=True)
    async def delserver(self, ctx, server_ip: str):
        """Removes a server from the checker"""
        server = ctx.message.server
        data = self.settings[server.id]
        to_remove = None
        for svr in data:
            if svr["server_ip"] == server_ip:
                to_remove = svr
                break
        else:
            await self.bot.say("I couldn't find that server in the list!")
            return
        data.remove(to_remove)
        self.settings[server.id] = data
        dataIO.save_json(self.settings_file, self.settings)
        await self.bot.say("Removed that server from the list!")

    def check_server(self, addr):
        mc_server = MinecraftServer.lookup(addr)
        query = None
        status = None

        try:
            query = mc_server.query()
        except socket.timeout:
            try:
                status = mc_server.status()
            except socket.timeout:
                print("Cannot reach server {}".format(addr))
            except ConnectionRefusedError:
                print("Connection refused")
        except ConnectionRefusedError:
            print("Connection refused")

        if query is not None:
            return query
        elif status is not None:
            return status
        else:
            return None

    async def get_server_embed(self, mc_server, server_ip):
        if mc_server is None:
            emb = discord.Embed(
                title="Server info for {}".format(server_ip)
            )
            emb.add_field(name="Online", value="No")
            return emb
        else:
            players = None
            brand = None
            motd = None
            if hasattr(mc_server, "software"):
                players = mc_server.players.names
                version = mc_server.software.version
                brand = mc_server.software.brand
                motd = mc_server.motd
            else:
                version = mc_server.version.name
            online_count = mc_server.players.online
            max_count = mc_server.players.max
            emb = discord.Embed(
                title="Server info for {}".format(server_ip)
            )
            emb.add_field(name="Online", value="Yes")
            emb.add_field(
                name="Online count",
                value="{}/{}".format(online_count, max_count)
            )
            if players:
                emb.set_footer(
                    text="Players online: {}".format(", ".join(players))
                )
            emb.add_field(name="Version", value=version)
            if brand:
                emb.add_field(name="Type", value=brand)
            if motd:
                emb.add_field(name="MOTD", value=motd)
            return emb

    async def mc_servers_check(self):
        CHECK_TIME = 120
        while self == self.bot.get_cog("Mcsvr"):
            bot_servers = list(self.bot.servers)
            for server in bot_servers:
                if server.id in self.settings:
                    for mc_svr in self.settings[server.id]:
                        channel_id = mc_svr["chn_id"]
                        channel = self.bot.get_channel(channel_id)
                        if channel is None:
                            continue
                        server_ip = mc_svr["server_ip"]
                        server_message = await self.bot.get_message(channel, mc_svr["server_message"])
                        loop = asyncio.get_event_loop()

                        mc_server = await loop.run_in_executor(None, partial(self.check_server, server_ip))

                        emb = await self.get_server_embed(mc_server, server_ip)
                        try:
                            await self.bot.edit_message(server_message, embed=emb)
                        except:
                            pass
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
