import asyncio
import logging
import time
from datetime import datetime as dt

import aiohttp
import asyncpraw
import asyncprawcore
import discord
from redbot.core import Config, commands, checks
from redbot.core.bot import Red

from redbot.core.utils.embed import randomize_colour
from redbot.core.i18n import Translator
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from .helpers import post_embed, private_only, get_color, get_subreddit

log = logging.getLogger("red.reddit")

_ = Translator("Reddit", __file__)

REDDIT_ACCESSTOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_OAUTH_API_ROOT = "https://oauth.reddit.com{}"
VALID_TOP_CONTROVERSIAL_TIMEFRAMES = ["hour", "day", "week", "month", "year", "all"]


class Reddit(commands.Cog):
    """Cog for getting things from Reddit's API"""

    default_global = {"client_id": "", "client_secret": "", "username": "", "password": "", "migration_complete": False}

    default_guild = {"modmail_channels": [], "posts_channels": []}

    default_channel = {"modmail": {}, "subreddits": {}}

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_global(**self.default_global)
        self.settings.register_guild(**self.default_guild)
        self.settings.register_channel(**self.default_channel)
        loop = asyncio.get_event_loop()
        self.migrator = loop.create_task(self._migrate_creds())
        self.reddit = None
        self.get_redditobj = loop.create_task(self._get_redditobj())

        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        if not self.session.closed:
            fut = asyncio.ensure_future(self.session.close())
            yield from fut.__await__()
    
    async def _get_redditobj(self):
        data = await self.bot.get_shared_api_tokens("reddit")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        username = data.get("username")
        password = data.get("password")
        user_agent = "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"

        self.reddit = asyncpraw.Reddit(
            client_id=client_id, 
            client_secret=client_secret, 
            username=username, 
            password=password, 
            user_agent=user_agent
        )
    
    async def _migrate_creds(self):
        migration_complete = await self.settings.migration_complete()
        if migration_complete:
            return
        client_id = await self.settings.client_id()
        client_secret = await self.settings.client_secret()
        username = await self.settings.username()
        password = await self.settings.password()
        if client_id and client_secret and username and password:
            await self.bot.set_shared_api_tokens(
                "reddit", 
                client_id=client_id, 
                client_secret=client_secret, 
                username=username, 
                password=password
            )
        # since we only actually want to move over to the shared tokens if we have
        # everything already, we'll just say that we've completed migration if we 
        # had everything and migrated or if we didn't have everything needed.
        await self.settings.migration_complete.set(True)

    @commands.command(name="reddituser")
    async def _user(self, ctx: commands.Context, username: str):
        """Commands for getting user info"""
        try:
            redditor = await self.reddit.redditor(username, fetch=True)
        except asyncprawcore.exceptions.NotFound:
            return await ctx.send("That user doesn't seem to exist!")
        
        created_at = dt.utcfromtimestamp(redditor.created_utc).strftime("%Y-%m-%d at %H:%M:%S UTC")
        footer = f"Created {created_at}"
        em = discord.Embed(
            title=redditor.name,
            url=f"https://reddit.com/u/{redditor.name}"
        )
        em = randomize_colour(em)
        em.set_footer(text=footer)
        em.add_field(name="Comment karma", value=redditor.comment_karma)
        em.add_field(name="Link karma", value=redditor.link_karma)
        if redditor.over_18:
            em.add_field(name="User subreddit is over 18?", value="Yes")
        else:
            em.add_field(name="User subreddit is over 18?", value="No")
        if redditor.is_gold:
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
        sub = await get_subreddit(self.reddit, ctx, subreddit)
        if sub is None:  # Error occurred in the request and we've already sent a message about it
            return
        
        created_at = dt.utcfromtimestamp(sub.created_utc).strftime("%Y-%m-%d at %H:%M:%S UTC")

        em = discord.Embed(
            title=sub.header_title,
            url=f"https://reddit.com{sub.url}",
            description=sub.public_description
        )
        color = get_color(sub)
        if not color:
            em = randomize_colour(em)
        else:
            em.color = discord.Color(value=int(color[1:], 16))
        em.add_field(name="Title", value=sub.title, inline=False)
        em.add_field(name="Created at", value=created_at, inline=False)
        em.add_field(name="Subreddit type", value=sub.subreddit_type, inline=False)
        em.add_field(name="Subscribers", value=sub.subscribers)
        em.add_field(name="Currently online", value=sub.accounts_active)
        if sub.over18:
            em.add_field(name="Subreddit is 18+?", value="Yes", inline=False)
        else:
            em.add_field(name="Subreddit is 18+?", value="No", inline=False)
        await ctx.send(embed=em)

    @_subreddit.command(name="hot")
    async def subreddit_hot(self, ctx: commands.Context, subreddit: str, post_count: int = 3):
        """Command for getting subreddit's hot posts"""
        if post_count <= 0 or post_count > 100:
            return await ctx.send("Sorry, I can't do that")
        sub = await get_subreddit(self.reddit, ctx, subreddit)
        if sub is None:  # Error occurred in the request and we've already sent a message about it
            return
        embeds = []
        async for post in sub.hot(limit=post_count):
            embeds.append(post_embed(post, ctx.message.created_at))
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @_subreddit.command(name="new")
    async def subreddit_new(self, ctx: commands.Context, subreddit: str, post_count: int = 3):
        """Command for getting subreddit's new posts"""
        if post_count <= 0 or post_count > 100:
            return await ctx.send("Sorry, I can't do that")
        sub = await get_subreddit(self.reddit, ctx, subreddit)
        if sub is None:  # Error occurred in the request and we've already sent a message about it
            return
        embeds = []
        async for post in sub.new(limit=post_count):
            embeds.append(post_embed(post, ctx.message.created_at))
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @_subreddit.command(name="top")
    async def subreddit_top(self, ctx: commands.Context, subreddit: str, time_frame: str="week", post_count: int = 3):
        """Command for getting subreddit's top posts"""
        if post_count <= 0 or post_count > 100:
            return await ctx.send("Sorry, I can't do that")
        else:
            if time_frame not in VALID_TOP_CONTROVERSIAL_TIMEFRAMES:
                time_frame = "week"

            sub = await get_subreddit(self.reddit, ctx, subreddit)
            if sub is None:  # Error occurred in the request and we've already sent a message about it
                return
            embeds = []
            async for post in sub.top(time_filter=time_frame, limit=post_count):
                embeds.append(post_embed(post, ctx.message.created_at))
            await menu(ctx, embeds, DEFAULT_CONTROLS)

    @_subreddit.command(name="controversial")
    async def subreddit_controversial(
        self, ctx: commands.Context, subreddit: str, time_frame: str="week", post_count: int = 3
    ):
        """Command for getting subreddit's controversial posts"""
        if post_count <= 0 or post_count > 100:
            return await ctx.send("Sorry, I can't do that")
        else:
            if time_frame not in VALID_TOP_CONTROVERSIAL_TIMEFRAMES:
                time_frame = "week"

            sub = await get_subreddit(self.reddit, ctx, subreddit)
            if sub is None:  # Error occurred in the request and we've already sent a message about it
                return
            embeds = []
            async for post in sub.top(time_filter=time_frame, limit=post_count):
                embeds.append(post_embed(post, ctx.message.created_at))
            await menu(ctx, embeds, DEFAULT_CONTROLS)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="redditset")
    async def _redditset(self, ctx: commands.Context):
        """Commands for setting reddit settings."""
        pass

    @checks.is_owner()
    @private_only()
    @_redditset.command(name="credentials", aliases=["creds"])
    async def set_creds(self, ctx: commands.Context):
        """
        Instructions to set the credentials needed to access Reddit's API
        """
        await ctx.send(
            "You can obtain your client id and secret by "
            "creating an app at https://www.reddit.com/prefs/apps\n"
            "Set the application url to http://127.0.0.1 and set "
            "the app type to script.\n\n"
            "The username and password are the username and password "
            "for the account you created the app (using the above "
            "instructions) on.\n\nTo set them, run the following command:\n\n"
            "`set api reddit client_id,<your client id> client_secret,<your client secret> username,<your reddit username> password,<your reddit password>`"
        )

    # End commands
