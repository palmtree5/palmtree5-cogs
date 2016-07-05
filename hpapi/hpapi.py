from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import discord
import aiohttp
import asyncio
import os
from __main__ import send_cmd_help

class hpapi():
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/hpapi/hpapi.json'
        settings = fileIO(self.settings_file, 'load')
        self.hpapi_key = settings['API_KEY']
        self.payload = {}
        self.payload["apikey"] = self.hpapi_key

    @commands.group(pass_context=True, no_pm=True, name="hp")
    async def _hpapi(self, ctx):
        """Get data from the Hypixel API"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_hpapi.command(pass_context=True, no_pm=True, name='booster')
    async def _booster(self, ctx):
        """Get active boosters. A game can be specified, in which case only the active booster for that game and the number of queued boosters for that game will be shown"""
        payload = self.payload
        url = 'http://api.hypixel.net/boosters?key=' + payload["apikey"]
        conn = aiohttp.TCPConnector(verify_ssl=False)
        sess = aiohttp.ClientSession(connector=conn)
        async with sess.get(url) as r:
            data = await r.json()
        if data["success"]:
            await self.bot.say('```{}```'.format(ctx))

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
    data = {}
    data["API_KEY"] = ''
    f = "data/hpapi/hpapi.json"
    if not fileIO(f, "check"):
        print("Creating default hpapi.json...")
        fileIO(f, "save", data)

def setup(bot):
    check_folder()
    check_file()
    n = hpapi(bot)
    bot.add_cog(n)
