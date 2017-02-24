from datetime import datetime as dt
import datetime
from random import choice as randchoice
import os
import aiohttp
import discord
from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO


numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


class SRRecords():
    """An interface for viewing speedrun records from speedrun.com"""
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/srrecords/settings.json")
    
    @commands.command(pass_context=True, no_pm=True)
    async def getrecords(self, ctx, game: str=None):
        """Gets records for the specified game"""
        server = ctx.message.server
        record_list = []
        if game is None:
            if server.id in self.settings["servers"]:
                game = self.settings["servers"][server.id]
            else:
                await self.bot.say("No game specified and no default for the server!")
        categories_url = "http://www.speedrun.com/api/v1/games/{}/categories".format(game)
        async with aiohttp.get(categories_url) as cat_req:
            cat_list = await cat_req.json()
        if "status" in cat_list and cat_list["status"] == 404:
            await self.bot.say(cat_list["message"])
        else:
            for cat in cat_list["data"]:
                cat_record = {}
                record_url = "http://speedrun.com/api/v1/leaderboards/{}/category/{}".format(game, cat["id"])
                async with aiohttp.get(record_url) as record_req:
                    lead_list = await record_req.json()
                async with aiohttp.get("http://speedrun.com/api/v1/games/{}".format(game)) as game_get:
                    game_info = await game_get.json()
                cat_record["game_name"] = game_info["data"]["names"]["international"]
                cat_record["cat_info"] = cat
                print(cat["id"])
                if "data" in lead_list:
                    if len(lead_list["data"]["runs"]) > 0:
                        cat_record["record"] = lead_list["data"]["runs"][0]
                        record_list.append(cat_record)
            await self.wr_menu(ctx, record_list, message=None, page=0, timeout=30)
        
    @checks.admin_or_permissions(manage_sever=True)
    @commands.group(pass_context=True)
    async def srset(self, ctx):
        """Speedrun settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.admin_or_permissions(manage_server=True)
    @srset.command(pass_context=True, no_pm=True, name="game")
    async def srset_game(self, ctx, game: str):
        """Sets the default game to get records for in this server.
        Use the name used for starting a race on SRL (i.e. oot = Ocarina of Time)"""
        url = "http://www.speedrun.com/api/v1/games/" + game
        async with aiohttp.get(url) as do_req:
            data = await do_req.json()
        if "status" in data and data["status"] == 404:
            await self.bot.say(data["message"])
        else:
            server = ctx.message.server
            if "servers" not in self.settings:
                self.settings["servers"] = {}
            self.settings["servers"][server.id] = game
            dataIO.save_json("data/srrecords/settings.json", self.settings)

    async def wr_menu(self, ctx, wr_list: list,
                      message: discord.Message=None,
                      page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        cur_page = wr_list[page]
        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                     for x in range(6)])
        colour = int(colour, 16)
        created_at = cur_page["record"]["run"]["submitted"]
        post_url = cur_page["record"]["run"]["weblink"]
        submit_time = "Submitted at " + created_at

        runner_url = cur_page["record"]["run"]["players"][0]["uri"]

        async with aiohttp.get(runner_url) as runner_get:
            runner_data = await runner_get.json()
        if "names" in runner_data["data"]:
            runner = runner_data["data"]["names"]["international"]
        else:
            runner = "Anonymous"
        desc = ""
        if cur_page["record"]["run"]["comment"] is None:
            desc = "No comments"
        else:
            desc = cur_page["record"]["run"]["comment"]
        emb = discord.Embed(title=cur_page["game_name"],
                            colour=discord.Colour(value=colour),
                            url=post_url,
                            description=desc)
        emb.add_field(name="Category", value=cur_page["cat_info"]["name"])
        emb.add_field(name="Runner", value=runner)
        emb.add_field(name="Time", value=str(datetime.timedelta(seconds=cur_page["record"]["run"]["times"]["primary_t"])))
        emb.set_footer(text=submit_time)
        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=emb)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")
            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=emb)
        react = await self.bot.wait_for_reaction(
            message=message, user=ctx.message.author, timeout=timeout,
            emoji=["➡", "⬅", "❌"]
        )
        if react is None:
            await self.bot.remove_reaction(message, "⬅", self.bot.user)
            await self.bot.remove_reaction(message, "❌", self.bot.user)
            await self.bot.remove_reaction(message, "➡", self.bot.user)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            next_page = 0
            if page == len(wr_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.wr_menu(ctx, wr_list, message=message,
                                      page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(wr_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.wr_menu(ctx, wr_list, message=message,
                                      page=next_page, timeout=timeout)
        else:
            return await\
                self.bot.delete_message(message)


def check_folder():
    if not os.path.isdir("data/srrecords"):
        os.mkdir("data/srrecords")


def check_file():
    data = {
        "servers": {}
    }
    if not dataIO.is_valid_json("data/srrecords/settings.json"):
        dataIO.save_json("data/srrecords/settings.json", {})

def setup(bot):
    check_folder()
    check_file()
    n = SRRecords(bot)
    bot.add_cog(n)
