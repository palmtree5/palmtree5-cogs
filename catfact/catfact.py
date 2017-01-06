import aiohttp
from discord.ext import commands


class Catfact():
    """A cog for getting a random cat fact"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True, pass_context=True, name="catfact")
    async def _catfact(self, ctx):
        """Gets a random cat fact"""
        async with aiohttp.get("http://catfacts-api.appspot.com/api/facts") as cfget:
            fact_json = await cfget.json()
        fact = fact_json["facts"][0]
        await self.bot.say("Ok " + ctx.message.author.mention + ", here is a cat fact.\n" + fact)



def setup(bot):
    n = Catfact(bot)
    bot.add_cog(n)
