import aiohttp
from discord.ext import commands
from __main__ import send_cmd_help


class Catfact():

    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True, pass_context=True, name="catfact")
    async def _catfact(self, ctx):
        """Gets a random cat fact"""
        with aiohttp.get("http://catfacts-api.appspot.com/api/facts") as cfget:
            fact = await cfget.json()["fact"]
        await self.bot.say("Ok " + ctx.message.author + ", here is a cat fact.\n" + fact)



def setup(bot):
    n = Coventry(bot)
    bot.add_cog(n)
