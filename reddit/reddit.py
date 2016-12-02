from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
from random import choice as randchoice
import aiohttp
import asyncio
import discord
import os
from datetime import datetime as dt

numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


class Reddit():

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/reddit/settings.json")
        self.access_token = ""

    async def get_access_token(self):
        auth =\
            aiohttp.helpers.BasicAuth(self.settings["client_id"],
                                      password=self.settings["client_secret"])
        post_data = {
                        "grant_type": "password",
                        "username": self.settings["username"],
                        "password": self.settings["password"]
                    }
        headers = {"User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"}
        async with\
                aiohttp.ClientSession(headers=headers, auth=auth) as session:
            async with\
                    session.post("https://www.reddit.com/api/v1/access_token",
                                 data=post_data) as req:
                req_json = await req.json()
                self.access_token = req_json["access_token"]
        await asyncio.sleep(3590)

    async def post_menu(self, ctx, post_list: list,
                        message: discord.Message=None,
                        page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        s = post_list[page]
        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                    for x in range(6)])
        colour = int(colour, 16)
        created_at = dt.utcfromtimestamp(s["data"]["created_utc"])
        created_at = created_at.strftime("%m/%d/%Y %H:%M:%S")
        post_url = "https://reddit.com" + s["data"]["permalink"]
        em = discord.Embed(title=s["data"]["title"],
                           colour=discord.Colour(value=colour),
                           url=post_url,
                           description=s["data"]["domain"])
        em.add_field(name="Author", value=s["data"]["author"])
        em.add_field(name="Created at", value=created_at)
        if s["data"]["stickied"]:
            em.add_field(name="Stickied", value="Yes")
        else:
            em.add_field(name="Stickied", value="No")
        em.add_field(name="Comments",
                     value=str(s["data"]["num_comments"]))
        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=em)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")
            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=em)
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
            if page == len(post_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.post_menu(ctx, post_list, message=message,
                                        page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(post_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.post_menu(ctx, post_list, message=message,
                                        page=next_page, timeout=timeout)
        else:
            return await\
                self.bot.delete_message(message)

    @commands.group(pass_context=True, name="reddit")
    async def _reddit(self, ctx):
        """Main Reddit command"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_reddit.command(pass_context=True, name="user")
    async def _user(self, ctx, username: str):
        """Commands for getting user info"""
        url = "https://oauth.reddit.com/user/{}/about".format(username)
        headers = {
                    "Authorization": "bearer " + self.access_token,
                    "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
                  }
        async with aiohttp.get(url, headers=headers) as req:
            resp_json = await req.json()
        resp_json = resp_json["data"]
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        created_at = dt.utcfromtimestamp(resp_json["created_utc"])
        desc = "Created at " + created_at.strftime("%m/%d/%Y %H:%M:%S")
        em = discord.Embed(title=resp_json["name"],
                           colour=discord.Colour(value=colour),
                           url="https://reddit.com/u/" + resp_json["name"],
                           description=desc)
        em.add_field(name="Comment karma", value=resp_json["comment_karma"])
        em.add_field(name="Link karma", value=resp_json["link_karma"])
        if "over_18" in resp_json and resp_json["over_18"]:
            em.add_field(name="Over 18?", value="Yes")
        else:
            em.add_field(name="Over 18?", value="No")
        if "is_gold" in resp_json and resp_json["is_gold"]:
            em.add_field(name="Is gold?", value="Yes")
        else:
            em.add_field(name="Is gold?", value="No")
        await self.bot.send_message(ctx.message.channel, embed=em)

    @commands.group(pass_context=True, name="subreddit")
    async def _subreddit(self, ctx):
        """Commands for getting subreddits"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_subreddit.command(pass_context=True, name="info")
    async def subreddit_info(self, ctx, subreddit: str):
        """Command for getting subreddit info"""
        url = "https://oauth.reddit.com/r/{}/about".format(subreddit)
        headers = {
                    "Authorization": "bearer " + self.access_token,
                    "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
                  }
        async with aiohttp.get(url, headers=headers) as req:
            resp_json = await req.json()
        resp_json = resp_json["data"]
        colour = ''.join([randchoice('0123456789ABCDEF') for x in range(6)])
        colour = int(colour, 16)
        created_at = dt.utcfromtimestamp(resp_json["created_utc"])
        created_at = created_at.strftime("%m/%d/%Y %H:%M:%S")
        em = discord.Embed(title=resp_json["url"],
                           colour=discord.Colour(value=colour),
                           url="https://reddit.com" + resp_json["url"],
                           description=resp_json["header_title"])
        em.add_field(name="Title", value=resp_json["title"])
        em.add_field(name="Created at", value=created_at)
        em.add_field(name="Subreddit type", value=resp_json["subreddit_type"])
        em.add_field(name="Subscriber count", value=resp_json["subscribers"])
        if resp_json["over18"]:
            em.add_field(name="Over 18?", value="Yes")
        else:
            em.add_field(name="Over 18?", value="No")
        await self.bot.send_message(ctx.message.channel, embed=em)

    @_subreddit.command(pass_context=True, name="hot")
    async def subreddit_hot(self, ctx, subreddit: str, post_count: int=3):
        """Command for getting subreddit's hot posts"""
        if post_count <= 0 or post_count > 100:
            await self.bot.say("Sorry, I can't do that")
        else:
            url = "https://oauth.reddit.com/r/{}/hot".format(subreddit)
            url += "?limit=" + str(post_count)
            headers = {
                    "Authorization": "bearer " + self.access_token,
                    "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
                }
            async with aiohttp.get(url, headers=headers) as req:
                resp_json = await req.json()
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(pass_context=True, name="new")
    async def subreddit_new(self, ctx, subreddit: str, post_count: int=3):
        """Command for getting subreddit's hot posts"""
        if post_count <= 0 or post_count > 100:
            await self.bot.say("Sorry, I can't do that")
        else:
            url = "https://oauth.reddit.com/r/{}/new".format(subreddit)
            url += "?limit=" + str(post_count)
            headers = {
                    "Authorization": "bearer " + self.access_token,
                    "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
                }
            async with aiohttp.get(url, headers=headers) as req:
                resp_json = await req.json()
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)
    @_subreddit.command(pass_context=True, name="top")
    async def subreddit_top(self, ctx, subreddit: str, post_count: int=3):
        """Command for getting subreddit's hot posts"""
        if post_count <= 0 or post_count > 100:
            await self.bot.say("Sorry, I can't do that")
        else:
            url = "https://oauth.reddit.com/r/{}/top".format(subreddit)
            url += "?limit=" + str(post_count)
            headers = {
                    "Authorization": "bearer " + self.access_token,
                    "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
                }
            async with aiohttp.get(url, headers=headers) as req:
                resp_json = await req.json()
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(pass_context=True, name="controversial")
    async def subreddit_controversial(self, ctx, subreddit: str,
                                      post_count: int=3):
        """Command for getting subreddit's hot posts"""
        if post_count <= 0 or post_count > 100:
            await self.bot.say("Sorry, I can't do that")
        else:
            url =\
                "https://oauth.reddit.com/r/{}/controversial".format(subreddit)
            url += "?limit=" + str(post_count)
            headers = {
                    "Authorization": "bearer " + self.access_token,
                    "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
                }
            async with aiohttp.get(url, headers=headers) as req:
                resp_json = await req.json()
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)

    @checks.is_owner()
    @commands.group(pass_context=True, name="redditset")
    async def _redditset(self, ctx):
        """Commands for setting reddit settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @_redditset.command(pass_context=True, name="clientid")
    async def set_clientid(self, ctx, client_id):
        """Sets the client id for the application"""
        self.settings["client_id"] = client_id
        dataIO.save_json("data/reddit/settings.json", self.settings)

    @checks.is_owner()
    @_redditset.command(pass_context=True, name="clientsecret")
    async def set_secret(self, ctx, client_secret):
        """Sets the client secret for the application"""
        self.settings["client_secret"] = client_secret
        dataIO.save_json("data/reddit/settings.json", self.settings)

    @checks.is_owner()
    @_redditset.command(pass_context=True, name="username")
    async def set_username(self, ctx, username):
        """Sets the username for the application"""
        self.settings["username"] = username
        dataIO.save_json("data/reddit/settings.json", self.settings)

    @checks.is_owner()
    @_redditset.command(pass_context=True, name="password")
    async def set_password(self, ctx, password):
        """Sets the password for the application"""
        self.settings["password"] = password
        dataIO.save_json("data/reddit/settings.json", self.settings)


def check_folder():
    if not os.path.exists("data/reddit"):
        print("Creating data/reddit folder")
        os.makedirs("data/reddit")


def check_file():
    f = "data/reddit/settings.json"
    if not dataIO.is_valid_json(f):
        data = {
                    "client_id": "",
                    "client_secret": "",
                    "username": "",
                    "password": ""
                }
        dataIO.save_json(f, data)


def setup(bot):
    check_folder()
    check_file()
    n = Reddit(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.get_access_token())
    bot.add_cog(n)
