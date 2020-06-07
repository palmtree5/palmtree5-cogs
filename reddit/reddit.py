import asyncio
import logging
import time
from datetime import datetime as dt

import aiohttp
import discord
from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import error
from redbot.core.utils.embed import randomize_colour
from redbot.core.i18n import Translator

from .menus import post_menu
from .errors import NoAccessTokenError, RedditAPIError, NotFoundError, AccessForbiddenError
from .helpers import make_request, private_only

log = logging.getLogger("red.reddit")

_ = Translator("Reddit", __file__)

REDDIT_ACCESSTOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_OAUTH_API_ROOT = "https://oauth.reddit.com{}"
VALID_TOP_CONTROVERSIAL_TIMEFRAMES = ["hour", "day", "week", "month", "year", "all"]


class Reddit(commands.Cog):
    """Cog for getting things from Reddit's API"""

    default_global = {"client_id": "", "client_secret": "", "username": "", "password": ""}

    default_guild = {"modmail_channels": [], "posts_channels": []}

    default_channel = {"modmail": {}, "subreddits": {}}

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_global(**self.default_global)
        self.settings.register_guild(**self.default_guild)
        self.settings.register_channel(**self.default_channel)
        loop = asyncio.get_event_loop()
        self.access_token_getter = loop.create_task(self.get_access_token())
        self.access_token = ""
        self.token_expiration_time = 0

        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        if not self.session.closed:
            fut = asyncio.ensure_future(self.session.close())
            yield from fut.__await__()

    @commands.command(name="reddituser")
    async def _user(self, ctx: commands.Context, username: str):
        """Commands for getting user info"""
        url = REDDIT_OAUTH_API_ROOT.format("/user/{}/about".format(username))
        headers = await self.get_headers()
        try:
            resp_json = await make_request(self.session, "GET", url, headers=headers)
        except NotFoundError as e:
            await ctx.send(str(e))
            return
        except AccessForbiddenError as e:
            await ctx.send(str(e))
            return
        except RedditAPIError as e:
            await ctx.send(str(e))
            return
        resp_json = resp_json["data"]
        created_at = dt.utcfromtimestamp(resp_json["created_utc"])
        desc = "Created at " + created_at.strftime("%m/%d/%Y %H:%M:%S")
        em = discord.Embed(
            title=resp_json["name"],
            url="https://reddit.com/u/" + resp_json["name"],
            description=desc,
        )
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
    async def _subreddit(self, ctx: commands.Context):
        """Commands for getting subreddits"""
        pass

    @_subreddit.command(name="info")
    async def subreddit_info(self, ctx: commands.Context, subreddit: str):
        """Command for getting subreddit info"""
        url = REDDIT_OAUTH_API_ROOT.format("/r/{}/about".format(subreddit))
        headers = await self.get_headers()
        try:
            resp_json = await make_request(self.session, "GET", url, headers=headers)
        except NotFoundError as e:
            await ctx.send(str(e))
            return
        except AccessForbiddenError as e:
            await ctx.send(str(e))
            return
        except RedditAPIError as e:
            await ctx.send(str(e))
            return
        resp_json = resp_json["data"]
        created_at = dt.utcfromtimestamp(resp_json["created_utc"]).strftime("%m/%d/%Y %H:%M:%S")
        em = discord.Embed(
            title=resp_json["url"],
            url="https://reddit.com" + resp_json["url"],
            description=resp_json["header_title"],
        )
        em = randomize_colour(em)
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
    async def subreddit_hot(self, ctx: commands.Context, subreddit: str, post_count: int = 3):
        """Command for getting subreddit's hot posts"""
        if post_count <= 0 or post_count > 100:
            await ctx.send("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/hot".format(subreddit))
            data = {"limit": post_count}
            headers = await self.get_headers()
            try:
                resp_json = await make_request(
                    self.session, "GET", url, headers=headers, params=data
                )
            except NotFoundError as e:
                await ctx.send(str(e))
                return
            except AccessForbiddenError as e:
                await ctx.send(str(e))
                return
            except RedditAPIError as e:
                await ctx.send(str(e))
                return
            resp_json = resp_json["data"]["children"]
            await post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(name="new")
    async def subreddit_new(self, ctx: commands.Context, subreddit: str, post_count: int = 3):
        """Command for getting subreddit's new posts"""
        if post_count <= 0 or post_count > 100:
            await ctx.send("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/new".format(subreddit))
            data = {"limit": post_count}
            headers = await self.get_headers()
            try:
                resp_json = await make_request(
                    self.session, "GET", url, headers=headers, params=data
                )
            except NotFoundError as e:
                await ctx.send(str(e))
                return
            except AccessForbiddenError as e:
                await ctx.send(str(e))
                return
            except RedditAPIError as e:
                await ctx.send(str(e))
                return
            resp_json = resp_json["data"]["children"]
            await post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(name="top")
    async def subreddit_top(self, ctx: commands.Context, subreddit: str, time_frame: str="week", post_count: int = 3):
        """Command for getting subreddit's top posts"""
        if post_count <= 0 or post_count > 100:
            await ctx.send("Sorry, I can't do that")
        else:
            if time_frame not in VALID_TOP_CONTROVERSIAL_TIMEFRAMES:
                time_frame = "week"
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/top".format(subreddit))
            data = {"limit": post_count, "t": time_frame}
            headers = await self.get_headers()
            try:
                resp_json = await make_request(
                    self.session, "GET", url, headers=headers, params=data
                )
            except NotFoundError as e:
                await ctx.send(str(e))
                return
            except AccessForbiddenError as e:
                await ctx.send(str(e))
                return
            except RedditAPIError as e:
                await ctx.send(str(e))
                return
            resp_json = resp_json["data"]["children"]
            await post_menu(ctx, resp_json, page=0, timeout=30)

    @_subreddit.command(name="controversial")
    async def subreddit_controversial(
        self, ctx: commands.Context, subreddit: str, time_frame: str="week", post_count: int = 3
    ):
        """Command for getting subreddit's controversial posts"""
        if post_count <= 0 or post_count > 100:
            await ctx.send("Sorry, I can't do that")
        else:
            if time_frame not in VALID_TOP_CONTROVERSIAL_TIMEFRAMES:
                time_frame = "week"
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/controversial".format(subreddit))
            data = {"limit": post_count, "t": time_frame}
            headers = await self.get_headers()
            try:
                resp_json = await make_request(
                    self.session, "GET", url, headers=headers, params=data
                )
            except NotFoundError as e:
                await ctx.send(str(e))
                return
            except AccessForbiddenError as e:
                await ctx.send(str(e))
                return
            except RedditAPIError as e:
                await ctx.send(str(e))
                return
            resp_json = resp_json["data"]["children"]
            await post_menu(ctx, resp_json, page=0, timeout=30)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="redditset")
    async def _redditset(self, ctx: commands.Context):
        """Commands for setting reddit settings."""
        pass

    @checks.is_owner()
    @private_only()
    @_redditset.command(name="credentials", aliases=["creds"])
    async def set_creds(
        self,
        ctx: commands.Context,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
    ):
        """
        Sets the credentials needed to access Reddit's API

        NOTE: This command should be done in a DM with the bot.
        
        You can obtain your client id and secret by 
        creating an app at https://www.reddit.com/prefs/apps 
        Set the application url to http://127.0.0.1 and set 
        the app type to script.
        
        The username and password are the username and password 
        for the account you created the app (using the above 
        instructions) on. Be sure to enter them in the correct 
        order. Failing to do so will cause the commands to fail
        """
        await self.settings.client_id.set(client_id)
        await self.settings.client_secret.set(client_secret)
        await self.settings.username.set(username)
        await self.settings.password.set(password)
        await ctx.send("Credentials set successfully!")
        await self.get_access_token()

    # End commands

    async def get_headers(self):
        remaining = self.token_expiration_time - dt.utcnow().timestamp()
        if remaining < 60:
            await self.get_access_token()
        if not self.access_token:  # No access token for some reason
            raise NoAccessTokenError("Have you set the credentials with `[p]redditset creds`?")
        user_agent = "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
        headers = {
            "Authorization": "bearer {}".format(self.access_token),
            "User-Agent": user_agent,
        }
        return headers

    async def get_access_token(self):
        client_id = await self.settings.client_id()
        client_secret = await self.settings.client_secret()
        username = await self.settings.username()
        password = await self.settings.password()
        if client_id and client_secret and username and password:
            auth = aiohttp.helpers.BasicAuth(client_id, password=client_secret)
            post_data = {"grant_type": "password", "username": username, "password": password}
            headers = {"User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"}
            response = await make_request(
                self.session,
                "POST",
                REDDIT_ACCESSTOKEN_URL,
                headers=headers,
                data=post_data,
                auth=auth,
            )
            if "error" in response:  # Something went wrong in the process
                owner = await self.bot.fetch_user(self.bot.owner_id)
                try:
                    await owner.send(
                        error(
                            "I tried to get an access token for the Reddit "
                            "cog but failed to do so because something was "
                            "wrong with the credentials you provided me. Try "
                            "setting them up again with `[p]redditset creds`, "
                            "ensuring that A) you copy and paste them "
                            "correctly, and B) that you put them in the "
                            "correct order when running the command"
                        )
                    )
                except discord.Forbidden:
                    log.warning(
                        "Something's wrong with the credentials for the "
                        "Reddit cog. I tried sending my owner a message "
                        "but that failed because I cannot send messages "
                        "to them.\nIt is recommended you do [p]redditset "
                        "creds and ensure you enter them correctly and in "
                        "the right order."
                    )
                self.toggle_commands(False)
                return
            self.access_token = response["access_token"]
            self.token_expiration_time = dt.utcnow().timestamp() + response["expires_in"]
            self.toggle_commands(True)
        else:
            self.toggle_commands(False)

    def toggle_commands(self, val: bool):
        reddituser_command = self.bot.get_command("reddituser")
        reddituser_command.enabled = val
        subreddit_command = self.bot.get_command("subreddit")
        subreddit_command.enabled = val
