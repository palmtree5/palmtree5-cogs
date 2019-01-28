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

from reddit.menus import post_menu
from .errors import NoAccessTokenError, RedditAPIError, NotFoundError, AccessForbiddenError
from .helpers import get_modmail_messages, make_request, private_only, get_subreddit_posts

log = logging.getLogger("red.reddit")

_ = Translator("Reddit", __file__)

REDDIT_ACCESSTOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_OAUTH_API_ROOT = "https://oauth.reddit.com{}"


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
        self.modmail_checker = loop.create_task(self.modmail_check())
        self.post_checker = loop.create_task(self.posts_check())
        self.access_token = ""
        self.token_expiration_time = 0

        self.session = aiohttp.ClientSession()

    def __unload(self):
        if not self.modmail_checker.cancelled():
            self.modmail_checker.cancel()
        if not self.post_checker.cancelled():
            self.post_checker.cancel()
        if not self.session.closed:
            fut = asyncio.ensure_future(self.session.close())
            yield from fut.__await__()

    async def __error(self, ctx, error):
        await ctx.send(
            _("Error in command {0.command.qualified_name}:\n\n{1.original}").format(ctx, error)
        )

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
        created_at = resp_json["created_utc"].strftime("%m/%d/%Y %H:%M:%S")
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
    async def subreddit_top(self, ctx: commands.Context, subreddit: str, post_count: int = 3):
        """Command for getting subreddit's top posts"""
        if post_count <= 0 or post_count > 100:
            await ctx.send("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/top".format(subreddit))
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

    @_subreddit.command(name="controversial")
    async def subreddit_controversial(
        self, ctx: commands.Context, subreddit: str, post_count: int = 3
    ):
        """Command for getting subreddit's controversial posts"""
        if post_count <= 0 or post_count > 100:
            await ctx.send("Sorry, I can't do that")
        else:
            url = REDDIT_OAUTH_API_ROOT.format("/r/{}/controversial".format(subreddit))
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

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def postnotify(self, ctx: commands.Context, subreddit: str):
        """
        Set up automatic posting of the specified subreddit's posts.
        """
        removed = False
        async with self.settings.channel(ctx.channel).subreddits() as subreddits:
            if subreddit in subreddits:
                del subreddits[subreddit]
                await ctx.send(_("Removed automatic posting of posts from {}").format(subreddit))
                removed = True
        if removed:
            async with self.settings.guild(ctx.guild).posts_channels() as posts_channels:
                if ctx.channel.id in posts_channels:
                    posts_channels.remove(ctx.channel.id)
            return

        url = REDDIT_OAUTH_API_ROOT.format("/r/{}/new".format(subreddit))
        data = {"limit": 1}
        headers = await self.get_headers()
        try:
            resp_json = await make_request(self.session, "GET", url, headers=headers, params=data)
        except NotFoundError as e:
            await ctx.send(str(e))
            return
        except AccessForbiddenError as e:
            await ctx.send(str(e))
            return
        except RedditAPIError as e:
            await ctx.send(str(e))
            return
        current_name = resp_json["data"]["children"][0]["data"]["name"]
        async with self.settings.channel(ctx.channel).subreddits() as subreddits:
            subreddits[subreddit] = current_name
        async with self.settings.guild(ctx.guild).posts_channels() as posts_channels:
            if ctx.channel.id not in posts_channels:
                posts_channels.append(ctx.channel.id)
        await ctx.tick()

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="redditset")
    async def _redditset(self, ctx: commands.Context):
        """Commands for setting reddit settings."""
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @_redditset.group(name="modmail", hidden=True)
    @commands.guild_only()
    async def modmail(self, ctx: commands.Context):
        """
        Commands for dealing with modmail settings
        NOTE: not really well tested
        """
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @modmail.command(name="enable")
    async def enable_modmail(
        self, ctx: commands.Context, subreddit: str, channel: discord.TextChannel
    ):
        """Enable posting modmail to the specified channel"""
        guild = ctx.guild

        await ctx.send(
            _(
                "WARNING: Anybody with access to {0.mention} will be able to see "
                "your subreddit's modmail messages. Therefore you should make "
                "sure that only your subreddit mods have access to that channel"
                ""
            ).format(
                channel
            )
        )
        await asyncio.sleep(5)
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
        if resp_json["user_is_moderator"]:
            async with self.settings.channel(channel).modmail() as mm:
                mm.update({subreddit: int(time.time())})
            async with self.settings.guild(ctx.guild).modmail_channels() as mm_chns:
                mm_chns.append(channel.id)
            await ctx.send("Enabled modmail for " + subreddit)
        else:
            await ctx.send("I'm sorry, this user does not appear " "to be a mod of that subreddit")

    @checks.admin_or_permissions(manage_guild=True)
    @modmail.command(name="disable")
    async def disable_modmail(
        self, ctx: commands.Context, subreddit: str, channel: discord.TextChannel
    ):
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
            "Authorization": "bearer {}".format(self.access_token), "User-Agent": user_agent
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
                owner = await self.bot.get_user_info(self.bot.owner_id)
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
        postnotify_command = self.bot.get_command("postnotify")
        postnotify_command.enabled = val
        subreddit_command = self.bot.get_command("subreddit")
        subreddit_command.enabled = val
        modmail_set_command = self.bot.get_command("redditset modmail")
        modmail_set_command.enabled = val

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
                                    task = asyncio.ensure_future(self.get_access_token())
                                    while not task.done():
                                        asyncio.sleep(5)
                                need_time_update = await get_modmail_messages(
                                    self.access_token, self.session, REDDIT_OAUTH_API_ROOT, channel, k
                                )
                                if need_time_update:
                                    current_sub.update({k: int(dt.utcnow().timestamp())})
            await asyncio.sleep(280)

    async def posts_check(self):
        await self.bot.wait_until_ready()
        while self == self.bot.get_cog("Reddit"):
            if not self.access_token:
                await asyncio.sleep(30)
                continue
            channels = await self.settings.all_channels()
            for ch_id, data in channels.items():
                channel = self.bot.get_channel(ch_id)
                if not channel:
                    continue
                for subreddit, last_name in data["subreddits"].items():
                    if (
                        not self.token_expiration_time
                        or self.token_expiration_time - dt.utcnow().timestamp() <= 60
                    ):
                        task = asyncio.ensure_future(self.get_access_token())
                        while not task.done():
                            await asyncio.sleep(5)
                    new_name = await get_subreddit_posts(
                        self.access_token, self.session, REDDIT_OAUTH_API_ROOT, channel, subreddit, last_name
                    )
                    if new_name:
                        async with self.settings.channel(channel).subreddits() as subs:
                            subs.update({subreddit: new_name})
            await asyncio.sleep(300)
