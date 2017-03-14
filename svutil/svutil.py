from discord.ext import commands
from .utils.dataIO import dataIO


class SVUtil():

    def __init__(self, bot):
        self.bot = bot
        self.luau_items = dataIO.load_json("data/svutil/luau.json")

    @commands.command()
    async def luausoup(self, item: str, quality: str):
        """Determine reaction from your addition to the soup
        Data from http://stardewvalleywiki.com/Luau"""
        for reaction in list(self.luau_items.keys()):
            if item.lower() in self.luau_items[reaction][quality.lower()]:
                await self.bot.say("Your {} quality {} will receive the {} reaction".format(quality, item, reaction))
                break
        else:
            await self.bot.say("That item was not found")


def setup(bot):
    bot.add_cog(SVUtil(bot))
