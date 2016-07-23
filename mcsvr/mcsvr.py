from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from mcstatus import MinecraftServer
import discord
import os
import datetime
import json
from __main__ import send_cmd_help

class Mcsvr():
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True, name="mcsvr")
    async def _mcsvr(self, ctx):
        """Commands for getting info about a Minecraft server"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
    @_mcsvr.command(pass_context=True, no_pm=True, name="count")
    async def _count(self, ctx, server_ip: str):
        """Gets player count for the specified server"""
        server = MinecraftServer.lookup(server_ip).status()
        online_count = server.players.online
        max_count = server.players.max
        message = "Player count for " + server_ip + ":\n\n" + str(online_count) + "/" + str(max_count)
        await self.bot.say("```{}```".format(message))
    @_mcsvr.command(pass_context=True, no_pm=True, name="version")
    async def _version(self, ctx, server_ip: str):
        """Gets information about the required Minecraft version for the specified server"""
        server = MinecraftServer.lookup(server_ip).status()
        message = "Required version for " + server_ip + ":\n\n" + str(server.version.name)
        await self.bot.say("```{}```".format(message))

def setup(bot):
    n = Mcsvr(bot)
    bot.add_cog(n)
