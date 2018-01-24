from random import choice as randchoice
from datetime import datetime as dt
from discord.ext import commands
import discord
import asyncio
from peony import events, PeonyClient

from redbot.core import Config, checks
from redbot.core.bot import Red
from redbot.core.context import RedContext

numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


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
        self.usr_loop = self.bot.loop.create_task(self.user_loop())

    def __unload(self):
        self.usr_loop.cancel()

    async def get_creds_and_client(self):
        self.creds = await self.get_creds()
        if self.creds is not None:
            self.client = await self.get_client()

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

    async def tweet_menu(self, ctx: RedContext, post_list: list,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        s = post_list[page]
        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                     for x in range(6)])
        colour = int(colour, 16)
        created_at = s.created_at
        post_url =\
            "https://twitter.com/{}/status/{}".format(s.user.screen_name, s.id)
        desc = "Created at: {}".format(created_at)
        em = discord.Embed(title="Tweet by {}".format(s.user.name),
                           colour=discord.Colour(value=colour),
                           url=post_url,
                           description=desc)
        em.add_field(name="Text", value=s.text)
        em.add_field(name="Retweet count", value=str(s.retweet_count))
        if hasattr(s, "extended_entities"):
            em.set_image(url=s.extended_entities["media"][0]["media_url"] + ":thumb")
        if not message:
            message =\
                await ctx.send(embed=em)
            await message.add_reaction("⬅")
            await message.add_reaction("❌")
            await message.add_reaction("➡")
        else:
            await message.edit(embed=em)

        def check_react(r, u):
            return u == ctx.author and r.emoji in ["➡", "⬅", "❌"]

        react, user = await self.bot.wait_for(
            "reaction_add", check=check_react
        )
        if react is None:
            await message.remove_reaction("⬅", ctx.guild.me)
            await message.remove_reaction("❌", ctx.guild.me)
            await message.remove_reaction("➡", ctx.guild.me)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.emoji]
        if react == "next":
            next_page = 0
            if page == len(post_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.tweet_menu(ctx, post_list, message=message,
                                         page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(post_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.tweet_menu(ctx, post_list, message=message,
                                         page=next_page, timeout=timeout)
        else:
            return await\
                message.delete()

    @commands.group(name='tweets')
    async def _tweets(self, ctx: RedContext):
        """Gets various information from Twitter's API"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_tweets.command(name='getuser')
    async def get_user(self, ctx: RedContext, username: str):
        """Get info about the specified user"""
        message = ""
        print(type(self.client))
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

    @_tweets.command(name='gettweets')
    async def get_tweets(self, ctx: RedContext, username: str, count: int):
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
            await self.tweet_menu(ctx, msg_list, page=0, timeout=30)
        else:
            await ctx.send("No tweets available to display!")

    @commands.group(name='tweetset')
    @checks.admin_or_permissions(manage_guild=True)
    async def _tweetset(self, ctx):
        """Command for setting required access information for the API.
        To get this info, visit https://apps.twitter.com and create a new application.
        Once the application is created, click Keys and Access Tokens then find the
        button that says Create my access token and click that. Once that is done,
        use the subcommands of this command to set the access details"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_tweetset.command(name="ignorementions")
    @checks.admin_or_permissions(manage_guild=True)
    async def tweetset_ignorementions(self, ctx: RedContext, toggle: str):
        """Toggle ignoring tweets starting with an @ mention
           toggle should be one of on or off"""
        if toggle.lower() == "on":
            await self.config.guild(ctx.guild).ignorementions.set(True)
            await ctx.send("@ mentions at the start of tweets will be ignored!")
        elif toggle.lower() == "off":
            await self.config.guild(ctx.guild).ignorementions.set(False)
            await ctx.send("@ mentions at the start of tweets will not be ignored!")
        else:
            await ctx.send("That isn't a valid input!")

    @_tweetset.command(name="channel")
    @checks.admin_or_permissions(manage_guild=True)
    async def tweetset_channel(self, ctx: RedContext, channel: discord.TextChannel):
        """Set the channel for the tweets stream to post to"""
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send("Channel set to {}!".format(channel.mention))
    
    @_tweetset.group(name="stream")
    @checks.admin_or_permissions(manage_guild=True)
    async def _stream(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_stream.group(name="user")
    @checks.admin_or_permissions(manage_guild=True)
    async def _user(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_user.command(name="add")
    @checks.admin_or_permissions(manage_guild=True)
    async def _add(self, ctx: RedContext, user_to_track):
        """Add a new tweet alert for the specified user"""
        tweets = await self.client.api.statuses.user_timeline.get(
            screen_name=user_to_track, count=1
        )
        for tweet in tweets:
            last_tweet = tweet
        current_streams = await self.config.guild(ctx.guild).streams()
        if current_streams:
            for stream in current_streams:
                if stream["username"] == user_to_track:
                    await ctx.send("Already tracking that user in this guild!")
                    return
        else:
            current_streams = []

        new_user = {
            "username": user_to_track,
            "last_id": last_tweet.id
        }

        current_streams.append(new_user)

        await self.config.guild(ctx.guild).streams.set(current_streams)

        await ctx.send("Added a tweet stream for the requested user!")

    @_user.command(name="remove")
    @checks.admin_or_permissions(manage_guild=True)
    async def _remove(self, ctx: RedContext, user_to_remove):
        if user_to_remove.lower() == "all":
            await self.config.guild(ctx.guild).clear()
            await ctx.send("Cleared the tracking list!")
        else:
            cur_list = await self.config.guild(ctx.guild).streams()
            user_out = [m for m in cur_list if m["username"] == user_to_remove][0]
            cur_list.remove(user_out)
            await self.config.guild(ctx.guild).streams.set(cur_list)
            await ctx.send("Removed the specified term!")

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

    async def user_loop(self):
        CHECK_TIME=120
        while self == self.bot.get_cog("Tweets"):
            for guild in self.bot.guilds:
                channel_id = await self.config.guild(guild).channel()
                if channel_id is None:
                    continue
                channel = guild.get_channel(channel_id)
                tweets_list = await self.config.guild(guild).streams()
                for stream in await self.config.guild(guild).streams():
                    new_tweets = await \
                        self.client.api.statuses.user_timeline.get(
                            screen_name=stream["username"], since_id=stream["last_id"]
                        )
                    new_data = {
                        "username": stream["username"],
                    }
                    have_set_new_lastid = False
                    for tweet in new_tweets:
                        if not have_set_new_lastid:
                            new_data["last_id"] = tweet.id
                            have_set_new_lastid = True
                        colour =\
                            ''.join([randchoice('0123456789ABCDEF')
                                    for x in range(6)])
                        colour = int(colour, 16)
                        created_at = tweet.created_at
                        post_url =\
                            "https://twitter.com/{}/status/{}".format(tweet.user.screen_name, tweet.id)
                        desc = "Created at: {}".format(created_at)
                        em = discord.Embed(title="Tweet by {}".format(tweet.user.name),
                                           colour=discord.Colour(value=colour),
                                           url=post_url,
                                           description=desc)
                        em.add_field(name="Text", value=tweet.text)
                        em.add_field(name="Retweet count", value=str(tweet.retweet_count))
                        if hasattr(tweet, "extended_entities"):
                            em.set_image(url=tweet.extended_entities["media"][0]["media_url"] + ":thumb")
                        await channel.send(embed=em)
                    tweets_list.remove(stream)
                    tweets_list.append(new_data)
                await self.config.guild(guild).streams.set(tweets_list)
            await asyncio.sleep(CHECK_TIME)

