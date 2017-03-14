from discord.ext import commands
from .utils.dataIO import dataIO
import discord
import math


class SVUtil():

    def __init__(self, bot):
        self.bot = bot
        self.luau_items = dataIO.load_json("data/svutil/luau.json")
        self.fair_items = dataIO.load_json("data/svutil/fair.json")

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
    
    @commands.command(pass_context=True)
    async def fairdisplay(self, ctx):
        """Calculates the point totals for the fair display"""
        author = ctx.message.author
        channel = ctx.message.channel
        await self.bot.say("Enter an item: ")
        items = []
        entry_done = False
        while not entry_done:
            item = None
            base_item = None
            msg = await self.bot.wait_for_message(timeout=30, author=author, channel=channel)
            if msg is None:
                await self.bot.say("You didn't enter anything!")
                return
            if msg.content.lower() == "done":
                entry_done = True
            else:
                try:
                    item = next(it for it in self.fair_items if it["Item"] == msg.content.lower())
                except StopIteration:
                    await self.bot.say("That item was not found. If it's the mayor's shorts, you'll get 750 star tokens")
                    return
                if item["Value"] == -1:
                    await self.bot.say("Enter the item use to make this {}".format(item["Item"]))
                    base_msg = await self.bot.wait_for_message(timeout=30, author=author, channel=channel)
                    if base_msg is None:
                        await self.bot.say("You didn't enter anything!")
                        return
                    try:
                        base_item = next(it for it in self.fair_items if it["Item"] == msg.content.lower())
                    except StopIteration:
                        await self.bot.say("That item was not found.")
                        return
                await self.bot.say("Enter the item's quality: ")
                qual_msg = await self.bot.wait_for_message(timeout=30, author=author, channel=channel)
                if qual_msg is None:
                    await self.bot.say("You didn't enter anything!")
                    return
                quality = qual_msg.content
                if base_item:
                    base_item_value = base_item["Value"]
                    if item["Item"] == "wine":
                        item["Value"] = math.floor(base_item_value * 3)
                    elif item["Item"] == "jelly" or item["Item"] == "pickles":
                        item["Value"] == math.floor(base_item_value * 2)
                    elif item["Item"] == "juice":
                        item["Value"] == math.floor(base_item_value * 2.25)
                item["Quality"] = quality.lower()
                items.append(item)
        score = 14  # Base score
        category_list = []
        for piece in items:
            category_list.append(piece["Category"])
            if item["Quality"] == "none":
                score += 1
            elif item["Quality"] == "silver":
                score += 2
            elif item["Quality"] == "gold":
                score += 3
            
            if item["Value"] > 400 and item["Quality"] is "none":
                score += 5
            elif item["Value"] > 300 and (item["Quality"] is "silver" or item["Quality"] is "none"):
                score += 4
            elif item["Value"] > 200:
                score += 3
            elif item["Value"] > 90:
                score += 2
            elif item["Value"] > 20:
                score += 1
            
        category_list = list(set(category_list))
        if len(category_list) > 6:
            score += 30
        else:
            score += len(category_list) * 5
        empty_penalty = 9 * (2 * (9 - len(items)))
        score += empty_penalty

        if score >= 90:
            await self.bot.say("You win first place!")
        elif score >= 75:
            await self.bot.say("You got second place!")
        elif score >= 60:
            await self.bot.say("You got third place!")
        else:
            await self.bot.say("You got fourth place!")
        
                
        
        



def setup(bot):
    bot.add_cog(SVUtil(bot))
