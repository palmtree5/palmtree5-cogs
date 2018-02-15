import asyncio
import os
import time
from copy import deepcopy
from datetime import datetime as dt
from random import choice as randchoice

import aiohttp
import discord
from discord.ext import commands
from redbot.core import Config, RedContext, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import warning
from redbot.core.utils.embed import randomize_colour

from .helpers import get_modmail_messages, make_request, private_only
from .errors import NoAccessTokenError

numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}

REDDIT_ACCESSTOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_OAUTH_API_ROOT = "https://oauth.reddit.com{}"

class Reddit:
    """Cog for getting things from Reddit's API"""

    default_global = {
        "client_id": "",
        "client_secret": "",
        "username": "",
        "password": ""
    }
    default_guild = {
        "modmail_channels": []
    }
    default_channel = {
        "modmail": {},
        "subreddits": {}
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_global(**self.default_global)
        self.settings.register_guild(**self.default_guild)
        self.settings.register_channel(**self.default_channel)
        loop = asyncio.get_event_loop()
        self.access_token_getter = loop.create_task(self.get_access_token())
        self.modmail_checker = loop.create_task(self.modmail_check())
        self.access_token = ""
        self.token_expiration_time = None

        self.session = aiohttp.ClientSession()

    def __unload(self):
        if not self.modmail_checker.cancelled():
            self.modmail_checker.cancel()
        if not self.session.closed:
            self.session.close()

    async def __error(self, ctx, error):
        await ctx.send("Error in command {0.command.qualified_name}:\n\n{1.original}".format(ctx, error))

    async def get_access_token(self):
        client_id = await self.settings.client_id()
        client_secret = await self.settings.client_secret()
        username = await self.settings.username()
        password = await self.settings.password()
        if client_id and client_secret and username and password:
            auth = aiohttp.helpers.BasicAuth(
                client_id,
                password=client_secret
            )
            post_data = {
                "grant_type": "password",
                "username": username,
                "password": password
            }
            headers = {"User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"}
            response = await make_request(
                self.session, "POST", REDDIT_ACCESSTOKEN_URL,
                headers=headers, data=post_data, auth=auth)
            self.access_token = response["access_token"]
            self.token_expiration_time = dt.utcnow().timestamp() + response["expires_in"]

    async def modmail_check(self):
        while self == self.bot.get_cog("Reddit"):
            for guild in self.bot.guilds:
                async with self.settings.guild(guild).modmail_channels() as mm_chns:
                    for chn in mm_chns:
                        channel = guild.get_channel(chn)
                        async with self.settings.channel(channel).modmail() as current_sub:
                            for k in current_sub:
                                if self.token_expiration_time - dt.utcnow().timestamp() <= 60:
                                    # close to token expiry time, so wait for a new token
                                    await asyncio.sleep(90)
                                need_time_update = await get_modmail_messages(
                                    self, REDDIT_OAUTH_API_ROOT, channel, k
                                )
                                if need_time_update:
                                    current_sub.update({k: int(dt.utcnow().timestamp())})
            await asyncio.sleep(280)

    async def post_menu(self, ctx: RedContext, post_list: list,
                        message: discord.Message=None,
                        page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        s = post_list[page]
        created_at = dt.utcfromtimestamp(s["data"]["created_utc"])
        created_at = created_at.strftime("%m/%d/%Y %H:%M:%S")
        post_url = "https://reddit.com" + s["data"]["permalink"]
        em = discord.Embed(title=s["data"]["title"],
                           url=post_url,
                           description=s["data"]["domain"])
        em = randomize_colour(em)
        em.add_field(name="Author", value=s["data"]["author"])
        em.add_field(name="Created at", value=created_at)
        if s["data"]["stickied"]:
            em.add_field(name="Stickied", value="Yes")
        else:
            em.add_field(name="Stickied", value="No")
        em.add_field(name="Comments",
                     value=str(s["data"]["num_comments"]))
        print(em.to_dict())
        if not message:
            message = await ctx.send(embed=em)
            await message.add_reaction("⬅")
            await message.add_reaction("❌")
            await message.add_reaction("➡")
        else:
            await message.edit(embed=em)
        
        def react_check(r, u):
            return u == ctx.author and str(r.emoji) in ["➡", "⬅", "❌"]

        try:
            react, user = await ctx.bot.wait_for(
                "reaction_add",
                check=react_check,
                timeout=timeout
            )
        except asyncio.TimeoutError:
            try:
                await message.clear_reactions()
            except discord.Forbidden:  # cannot remove all reactions
                await message.remove_reaction("⬅", ctx.guild.me)
                await message.remove_reaction("❌", ctx.guild.me)
                await message.remove_reaction("➡", ctx.guild.me)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.emoji]
        if react == "next":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("➡", ctx.author)
                except discord.NotFound:
                    pass
            if page == len(post_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.post_menu(ctx, post_list, message=message,
                                        page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("⬅", ctx.author)
                except discord.NotFound:
                    pass
            if page == 0:
                next_page = len(post_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.post_menu(ctx, post_list, message=message,
                                        page=next_page, timeout=timeout)
        else:
            return await message.delete()

    @commands.group(name="reddit")
    async def _reddit(self, ctx: RedContext):
        """Main Reddit command"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_reddit.command(name="user")
    async def _user(self, ctx: RedContext, username: str):
        """Commands for getting user info"""
        url = REDDIT_OAUTH_API_ROOT.format("/user/{}/about".format(username))
        remaining = self.token_expiration_time - dt.utcnow().timestamp()
        if remaining < 60:
            await self.get_access_token()
        if not self.access_token:  # No access token for some reason
            raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
        headers = {
            "Authorization": "bearer " + self.access_token,
            "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
        }
        resp_json = await make_request(self.session, "GET", url, headers=headers)
        resp_json = resp_json["data"]
        created_at = dt.utcfromtimestamp(resp_json["created_utc"])
        desc = "Created at " + created_at.strftime("%m/%d/%Y %H:%M:%S")
        em = discord.Embed(title=resp_json["name"],
                           url="https://reddit.com/u/" + resp_json["name"],
                           description=desc)
        em = randomize_colour(em)
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
        await ctx.send(embed=em)

    @commands.group(name="subreddit")
    async def _subreddit(self, ctx: RedContext):
        """Commands for getting subreddits"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_subreddit.command(name="info")
    async def subreddit_info(self, ctx: RedContext, subreddit: str):
        """Command for getting subreddit info"""
        url = REDDIT_OAUTH_API_ROOT.format("/r/{}/about".format(subreddit))
        remaining = self.token_expiration_time - dt.utcnow().timestamp()
        if remaining < 60:
            await self.get_access_token()
        if not self.access_token:  # No access token for some reason
            raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
        headers = {
            "Authorization": "bearer " + self.access_token,
            "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
        }
        resp_json = await make_request(self.session, "GET", url, headers=headers)
        if "data" not in resp_json and resp_json["error"] == 403:
            await ctx.send("Sorry, I don't have access to that subreddit")
            return
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
        await ctx.send(embed=em)

    @_subreddit.command(name="hot")
    async def subreddit_hot(self, ctx: RedContext, subreddit: str, post_count: int=3):
        """Command for getting subreddit's hot posts"""
        if post_count <= 0 or post_count > 100:
            await self.bot.say("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/hot".format(subreddit))
            url += "?limit={}".format(post_count)
            remaining = self.token_expiration_time - dt.utcnow().timestamp()
            if remaining < 60:
                await self.get_access_token()
            if not self.access_token:  # No access token for some reason
                raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
            headers = {
                "Authorization": "bearer " + self.access_token,
                "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
            }
            resp_json = await make_request(self.session, "GET", url, headers=headers)
            if "data" not in resp_json and resp_json["error"] == 403:
                await self.bot.say("Sorry, the currently authenticated account does not have access to that subreddit")
                return
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(name="new")
    async def subreddit_new(self, ctx: RedContext, subreddit: str, post_count: int=3):
        """Command for getting subreddit's new posts"""
        if post_count <= 0 or post_count > 100:
            await ctx.send("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/new".format(subreddit))
            url += "?limit={}".format(post_count)
            remaining = self.token_expiration_time - dt.utcnow().timestamp()
            if remaining < 60:
                await self.get_access_token()
            if not self.access_token:  # No access token for some reason
                raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
            headers = {
                "Authorization": "bearer " + self.access_token,
                "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
            }
            resp_json = await make_request(self.session, "GET", url, headers=headers)
            if "data" not in resp_json and resp_json["error"] == 403:
                await ctx.send("Sorry, the currently authenticated account does not have access to that subreddit")
                return
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(name="top")
    async def subreddit_top(self, ctx: RedContext, subreddit: str, post_count: int=3):
        """Command for getting subreddit's top posts"""
        if post_count <= 0 or post_count > 100:
            await self.bot.say("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/top".format(subreddit))
            url += "?limit={}".format(post_count)
            remaining = self.token_expiration_time - dt.utcnow().timestamp()
            if remaining < 60:
                await self.get_access_token()
            if not self.access_token:  # No access token for some reason
                raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
            headers = {
                "Authorization": "bearer " + self.access_token,
                "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
            }
            resp_json = await make_request(self.session, "GET", url, headers=headers)
            if "data" not in resp_json and resp_json["error"] == 403:
                await self.bot.say("Sorry, the currently authenticated account does not have access to that subreddit")
                return
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(name="controversial")
    async def subreddit_controversial(self, ctx: RedContext, subreddit: str,
                                      post_count: int=3):
        """Command for getting subreddit's controversial posts"""
        if post_count <= 0 or post_count > 100:
            await self.bot.say("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/controversial".format(subreddit))
            url += "?limit={}".format(post_count)
            remaining = self.token_expiration_time - dt.utcnow().timestamp()
            if remaining < 60:
                await self.get_access_token()
            if not self.access_token:  # No access token for some reason
                raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
            headers = {
                "Authorization": "bearer " + self.access_token,
                "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
            }
            resp_json = await make_request(self.session, "GET", url, headers=headers)
            if "data" not in resp_json and resp_json["error"] == 403:
                await self.bot.say("Sorry, the currently authenticated account does not have access to that subreddit")
                return
            resp_json = resp_json["data"]["children"]
            await self.post_menu(ctx, resp_json, page=0, timeout=30)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="redditset")
    async def _redditset(self, ctx: RedContext):
        """Commands for setting reddit settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @checks.admin_or_permissions(manage_guild=True)
    @_redditset.group(name="modmail")
    @commands.guild_only()
    async def modmail(self, ctx: RedContext):
        """
        Commands for dealing with modmail settings
        NOTE: not really well tested
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @checks.admin_or_permissions(manage_guild=True)
    @modmail.command(name="enable")
    async def enable_modmail(self, ctx: RedContext, subreddit: str,
                             channel: discord.TextChannel):
        """Enable posting modmail to the specified channel"""
        guild = ctx.guild
        await ctx.send("WARNING: Anybody with access to "
                        + channel.mention + " will be able to see " +
                        "your subreddit's modmail messages." +
                        "Therefore you should make sure that only " +
                        "your subreddit mods have access to that channel")
        await asyncio.sleep(5)
        url = REDDIT_OAUTH_API_ROOT.format("/r/{}/about".format(subreddit))
        remaining = self.token_expiration_time - dt.utcnow().timestamp()
        if remaining < 60:
            await self.get_access_token()
        if not self.access_token:  # No access token for some reason
            raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
        headers = {
            "Authorization": "bearer " + self.access_token,
            "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
        }
        resp_json = await make_request(self.session, "GET", url, headers=headers)
        resp_json = resp_json["data"]
        if resp_json["user_is_moderator"]:
            async with self.settings.channel(channel).modmail() as mm:
                mm.update({subreddit: int(time.time())})
            async with self.settings.guild(ctx.guild).modmail_channels() as mm_chns:
                mm_chns.append(channel.id)
            await ctx.send("Enabled modmail for " + subreddit)
        else:
            await ctx.send("I'm sorry, this user does not appear to be " +
                               "a mod of that subreddit")

    @checks.admin_or_permissions(manage_guild=True)
    @modmail.command(name="disable")
    async def disable_modmail(self, ctx: RedContext, subreddit: str, channel: discord.TextChannel):
        """Disable modmail posting to discord"""
        async with self.settings.channel(channel).modmail() as mm:
            try:
                mm.pop(subreddit)
            except KeyError:
                await ctx.send(
                    "It doesn't appear modmail posting is enabled for "
                    "that subreddit in the specified channel!"
                )
                return
        async with self.settings.guild(ctx.guild).modmail_channels() as mm_chns:
            try:
                mm_chns.remove(channel.id)
            except ValueError:
                await ctx.send("Channel not in the modmail channel list...")
                return
        await ctx.send("Disabled modmail posting for this server")

    @checks.is_owner()
    @private_only()
    @_redditset.command(name="credentials", aliases=["creds"])
    async def set_creds(self, ctx: RedContext, 
            client_id: str, client_secret: str, 
            username: str, password: str):
        """
        Sets the credentials needed to access Reddit's API
        
        You can obtain your client id and secret by
        creating an app at https://www.reddit.com/prefs/apps
        Set the application url to http://127.0.0.1 and set
        the app type to script.
        
        The username and password are the username and password
        for the account you created the app (using the above 
        instructions) on.
        """
        await self.settings.client_id.set(client_id)
        await self.settings.client_secret.set(client_secret)
        await self.settings.username.set(username)
        await self.settings.password.set(password)
        await ctx.send("Credentials set successfully!")
        await self.get_access_token()
