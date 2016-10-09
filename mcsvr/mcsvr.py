from discord.ext import commands
from .utils import checks
try:
    from mcstatus import MinecraftServer
    mcstatusInstalled = True
except:
    mcstatusInstalled = False
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
        message = "Player count for " + server_ip + ":\n\n" + \
            str(online_count) + "/" + str(max_count)
        await self.bot.say("```{}```".format(message))

    @_mcsvr.command(pass_context=True, no_pm=True, name="version")
    async def _version(self, ctx, server_ip: str):
        """
        Gets information about the required Minecraft
        version for the specified server
        """
        server = MinecraftServer.lookup(server_ip).status()
        message = "Server version for " + server_ip + ":\n\n" + \
            str(server.version.name)
        await self.bot.say("```{}```".format(message))

    @checks.admin_or_permissions(manage_server=True)
    @commands.group(pass_context=True, name="mcsvrset")
    async def _mcsvrset(self, ctx):
        """Settings for being notified of server issues"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @checks.admin_or_permissions(manage_server=True)
    @_mcsvrset.command(pass_context=True, name="chan")
    async def set_chan(self, ctx, name):
        pass


def setup(bot):
    if mcstatusInstalled:
        n = Mcsvr(bot)
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to do 'pip3 install mcstatus'")
