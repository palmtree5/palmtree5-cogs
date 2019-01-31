import asyncio
import datetime
import os
from datetime import datetime as dt
from random import choice as randchoice

import aiohttp
import discord
from redbot.core import Config, checks, commands
from redbot.core.i18n import Translator

numbs = {"next": "➡", "back": "⬅", "exit": "❌"}


class SRRecords(commands.Cog):
    """An interface for viewing speedrun records from speedrun.com"""

    default_guild = {"game": ""}

    def __init__(self):
        self.config = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.config.register_guild(**self.default_guild)
        self.session = aiohttp.ClientSession()

    @commands.command()
    async def getrecords(self, ctx, game: str = None):
        """Gets records for the specified game"""
        guild = ctx.guild

        record_list = []
        if game is None:
            game = await self.config.guild(guild).game() if guild else None
            if not game:
                if guild is None:
                    await ctx.send(
                        "No game specified and cannot find a default "
                        "because the command was not run in a server!"
                    )
                else:
                    await ctx.send("No game specified and no default for the server!")
                return
        categories_url = "http://www.speedrun.com/api/v1/games/{}/categories".format(game)
        async with self.session.get(categories_url) as cat_req:
            cat_list = await cat_req.json()
        if "status" in cat_list and cat_list["status"] == 404:
            await ctx.send("An error occurred!")
            await ctx.send(cat_list["message"])
        else:
            for cat in cat_list["data"]:
                cat_record = {}
                record_url = "http://speedrun.com/api/v1/leaderboards/{}/category/{}".format(
                    game, cat["id"]
                )
                async with self.session.get(record_url) as record_req:
                    lead_list = await record_req.json()
                async with self.session.get(
                    "http://speedrun.com/api/v1/games/{}".format(game)
                ) as game_get:
                    game_info = await game_get.json()
                cat_record["game_name"] = game_info["data"]["names"]["international"]
                cat_record["cat_info"] = cat
                if "data" in lead_list:
                    if len(lead_list["data"]["runs"]) > 0:
                        cat_record["record"] = lead_list["data"]["runs"][0]
                        record_list.append(cat_record)
            await self.wr_menu(ctx, record_list, message=None, page=0, timeout=30)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group()
    async def srset(self, ctx):
        """Speedrun settings"""
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @srset.command(name="game")
    @commands.guild_only()
    async def srset_game(self, ctx, game: str):
        """Sets the default game to get records for in this server."""
        url = "http://www.speedrun.com/api/v1/games/" + game

        async with self.session.get(url) as do_req:
            data = await do_req.json()
        if "status" in data and data["status"] == 404:
            await ctx.send(data["message"])
        else:
            await self.config.guild(ctx.guild).game.set(game)

    async def wr_menu(
        self, ctx, wr_list: list, message: discord.Message = None, page=0, timeout: int = 30
    ):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        cur_page = wr_list[page]
        colour = "".join([randchoice("0123456789ABCDEF") for x in range(6)])
        colour = int(colour, 16)
        created_at = cur_page["record"]["run"]["submitted"]
        post_url = cur_page["record"]["run"]["weblink"]
        submit_time = "Submitted at " + created_at

        runner_url = cur_page["record"]["run"]["players"][0]["uri"]
        async with aiohttp.ClientSession() as session:
            async with self.session.get(runner_url) as runner_get:
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
        emb = discord.Embed(
            title=cur_page["game_name"],
            colour=discord.Colour(value=colour),
            url=post_url,
            description=desc,
        )
        emb.add_field(name="Category", value=cur_page["cat_info"]["name"])
        emb.add_field(name="Runner", value=runner)
        emb.add_field(
            name="Time",
            value=str(datetime.timedelta(seconds=cur_page["record"]["run"]["times"]["primary_t"])),
        )
        emb.set_footer(text=submit_time)
        if not message:
            message = await ctx.send(embed=emb)
            await message.add_reaction("⬅")
            await message.add_reaction("❌")
            await message.add_reaction("➡")
        else:
            await message.edit(embed=emb)

        def react_check(reaction: discord.Reaction, user):
            if str(reaction.emoji) in numbs.values() and user == ctx.author:
                return True
            return False

        try:
            react, user = await ctx.bot.wait_for(
                "reaction_add", timeout=timeout, check=react_check
            )
        except asyncio.TimeoutError:
            await message.remove_reaction("⬅", ctx.guild.me)
            await message.remove_reaction("❌", ctx.guild.me)
            await message.remove_reaction("➡", ctx.guild.me)
            return None
        else:
            reacts = {v: k for k, v in numbs.items()}
            react = reacts[str(react)]
        if react == "next":
            next_page = 0
            if page == len(wr_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.wr_menu(
                ctx, wr_list, message=message, page=next_page, timeout=timeout
            )
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(wr_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.wr_menu(
                ctx, wr_list, message=message, page=next_page, timeout=timeout
            )
        else:
            return await message.delete()
