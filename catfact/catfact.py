import aiohttp
from discord.ext import commands


class Catfact():
    """A cog for getting a random cat fact"""
    def __init__(self, bot):
        self.bot = bot
        #self.session = aiohttp.ClientSession()

    @commands.command(pass_context=True, name="catfact")
    async def _catfact(self, ctx):
        """Gets a random cat fact"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    "http://catfacts-api.appspot.com/api/facts",
                    headers={"Accept": "text/javascript"}
                    ) as cfget:
                fact_json = await cfget.json(content_type=None)
        fact = fact_json["facts"][0]
        await ctx.send("Ok " + ctx.message.author.mention + ", here is a cat fact.\n" + fact)

