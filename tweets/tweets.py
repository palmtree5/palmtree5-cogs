import asyncio
from random import choice as randchoice

import discord
from discord.ext import commands
from peony import PeonyClient
from redbot.core import Config, checks
from redbot.core.bot import Red
from redbot.core.context import RedContext

from .errors import NoClientException
from .menus import tweet_menu


class Tweets:
    """Cog for displaying info from Twitter's API"""
    default_global = {
        "consumer_key": None,
        "consumer_secret": None,
        "access_token": None,
        "access_secret": None
    }

    default_guild = {
        "streams": [],
        "ignorementions": False,
        "channel": None
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 55755755)
        self.config.register_global(**self.default_global)
        self.config.register_guild(**self.default_guild)
        self.creds = None
        self.client = None
        self.bot.loop.create_task(self.get_creds_and_client())
    
    async def __error(self, ctx, error):
        await ctx.send("Error in `{0.command.qualified_name}`:\n\n{1.original}".format(ctx, error))

    async def get_creds_and_client(self):
        self.creds = await self.get_creds()
        cmd1 = self.bot.get_command("gettweets")
        cmd2 = self.bot.get_command("getuser")
        if self.creds is not None:
            self.client = await self.get_client()
            if not cmd1.enabled:
                cmd1.enabled = True
                cmd2.enabled = True
        else:
            cmd1.enabled = False
            cmd2.enabled = False

    async def get_client(self):
        if self.creds["consumer_key"] is None or self.creds["consumer_secret"] is None or\
                self.creds["access_token"] is None or self.creds["access_token_secret"] is None:
            return None
        else:
            return PeonyClient(**self.creds)

    async def get_creds(self):
        consumer_key = await self.config.consumer_key()
        consumer_secret = await self.config.consumer_secret()
        access_token = await self.config.access_token()
        access_secret = await self.config.access_secret()
        if not consumer_key or not consumer_secret or not access_token\
                or not access_secret:
            return None
        return {
            "consumer_key": consumer_key,
            "consumer_secret": consumer_secret,
            "access_token": access_token,
            "access_token_secret": access_secret
        }

    @commands.command(name='getuser')
    async def get_user(self, ctx: RedContext, username: str):
        """Get info about the specified user"""
        message = ""
        if self.client is None:
            raise NoClientException("Have you set the access credentials with `[p]tweetset creds`?")
        user = await self.client.api.users.show.get(screen_name=username)

        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                 for x in range(6)])
        colour = int(colour, 16)
        url = "https://twitter.com/" + user.screen_name
        emb = discord.Embed(title=user.name,
                            colour=discord.Colour(value=colour),
                            url=url,
                            description=user.description)
        emb.set_thumbnail(url=user.profile_image_url)
        emb.add_field(name="Followers", value=user.followers_count)
        emb.add_field(name="Friends", value=user.friends_count)
        if user.verified:
            emb.add_field(name="Verified", value="Yes")
        else:
            emb.add_field(name="Verified", value="No")
        footer = "Created at " + user.created_at
        emb.set_footer(text=footer)
        await ctx.send(embed=emb)

    @commands.command(name='gettweets')
    async def get_tweets(self, ctx: RedContext, username: str, count: int=5):
        """Gets the specified number of tweets for the specified username"""
        if count > 25:
            count = 25
        elif count < 1:
            await ctx.send("I can't do that, silly! Please specify a \
                number greater than or equal to 1")
            return

        msg_list = await self.client.api.statuses.user_timeline.get(
            screen_name=username, count=count
        )

        if len(msg_list) > 0:
            await tweet_menu(ctx, msg_list, page=0, timeout=30)
        else:
            await ctx.send("No tweets available to display!")

    @commands.group(name='tweetset')
    @checks.admin_or_permissions(manage_guild=True)
    async def _tweetset(self, ctx):
        """Command for setting required access information for the API."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            await ctx.send(
                "To get the access info, visit https://apps.twitter.com and "
                "create a new application. Once the application is created, "
                "click Keys and Access Tokens then find the button that says "
                "'Create my access token' and click that."
            )

    @_tweetset.command(name='creds')
    @checks.is_owner()
    async def set_creds(self, ctx: RedContext, consumer_key: str, consumer_secret: str, access_token: str, access_secret: str):
        """Sets the access credentials. See [p]help tweetset for instructions on getting these"""
        await self.config.consumer_key.set(consumer_key)
        await self.config.consumer_secret.set(consumer_secret)
        await self.config.access_token.set(access_token)
        await self.config.access_secret.set(access_secret)

        # Attempt to get the client going after setting creds
        self.creds = await self.get_creds()
        self.client = self.get_client()
        await ctx.send('Set the access credentials!')
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("I tried to delete your message but I don't have permissions to do so!")
