from discord.ext import commands
from .utils import checks
from .utils.dataIO import fileIO
try:
    import praw
    prawInstalled = True
except:
    prawInstalled = False
try:
    import OAuth2Util as o2u
    o2uInstalled = True
except:
    o2uInstalled = False
import datetime as dt
import os
import configparser as c
from __main__ import send_cmd_help
import logging
log = logging.getLogger('red.reddit')


class Reddit():

    def __init__(self, bot):
        self.bot = bot
        cfg_file = "./data/reddit/oauth.json"
        settings = fileIO(cfg_file, "load")
        if settings["app_key"] and settings["app_secret"]:
            try:
                self.r = praw.Reddit("RedBotRedditCog/v0.1 by /u/palmtree5")
                print("Authorizing")
                self.o = \
                    o2u.OAuth2Util(self.r, app_key=settings["app_key"],
                                app_secret=settings["app_secret"],
                                scope=settings["scope"],
                                refreshable=settings["refreshable"],
                                configfile="data/reddit/oauth.ini",
                                server_mode=settings["server_mode"])
                print("Refreshing")
                self.o.refresh(force=True)
            except praw.errors.OAuthException:
                log.warning("Uh oh, something went wrong! Did you set the client \
                    key and secret?")

    @commands.group(pass_context=True, no_pm=True, name="reddit")
    async def _reddit(self, ctx):
        """Main Reddit command"""
        if ctx.invoked_subcommand is None:
            send_cmd_help(ctx)

    @_reddit.group(pass_context=True, no_pm=True, name="posts")
    async def _posts(self, ctx):
        """Commands for getting posts"""
        if ctx.invoked_subcommand is None:
            send_cmd_help(ctx)

    @_posts.command(pass_context=True, no_pm=True, name="new")
    async def new_posts(self, ctx, subreddit, count: int=1):
        """Get the specified number of posts from the specified subreddit,
        sorted by new"""
        message = "The " + str(count) + " newest posts for /r/" + subreddit\
            + "\n\n"
        for submission in self.r.get_subreddit(subreddit, fetch=True).\
                get_new(limit=count):
            message += submission.title + ":      https://redd.it" +\
                submission.id + "\n"
        await self.bot.say('```{}```'.format(message))

    @_posts.command(pass_context=True, no_pm=True, name="hot")
    async def hot_posts(self, ctx, subreddit, count: int=1):
        """Get the specified number of posts from the specified subreddit,
        sorted by hot"""
        message = "The " + str(count) + " hottest posts for /r/" + subreddit\
            + "\n\n"
        for submission in self.r.get_subreddit(subreddit, fetch=True).\
                get_hot(limit=count):
            message += submission.title + ":      https://redd.it" +\
                submission.id + "\n"
        await self.bot.say('```{}```'.format(message))

    @checks.is_owner()
    @commands.group(pass_context=True, name="redditset")
    async def _redditset(self, ctx):
        """Commands for setting reddit settings"""
        if ctx.invoked_subcommand is None:
            send_cmd_help(ctx)

    @checks.is_owner()
    @_redditset.command(pass_context=True, name="key")
    async def set_key(self, ctx, key):
        """Sets the app key for the application"""
        settings = fileIO("data/reddit/oauth.json", "load")
        settings["app_key"] = key
        fileIO("data/reddit/oauth.json", "save", settings)
        await self.bot.say("Set the app key!")

    @checks.is_owner()
    @_redditset.command(pass_context=True, name="secret")
    async def set_secret(self, ctx, secret):
        """Sets the app secret for the application"""
        settings = fileIO("data/reddit/oauth.json", "load")
        settings["app_secret"] = secret
        fileIO("data/reddit/oauth.json", "save", settings)
        await self.bot.say("Set the app secret!")

    @checks.is_owner()
    @_redditset.command(pass_context=True, name="useragent")
    async def set_useragent(self, ctx, useragent: str):
        """Sets the user agent string sent for the application"""
        settings = fileIO("data/reddit/oauth.json", "load")
        settings["UserAgent"] = useragent
        fileIO("data/reddit/oauth.json", "save", settings)
        await self.bot.say("Set the user agent!")


def check_folder():
    if not os.path.exists("data/reddit"):
        log.info("Creating data/reddit folder")
        os.makedirs("data/reddit")


def check_file():
    f = "data/reddit/oauth.json"
    if not fileIO(f, "check"):
        log.info("Creating default oauth.json...")
        data = {"UserAgent": "", "scope": "read", "refreshable": True,
                "app_key": "", "app_secret": "", "server_mode": False,
                "url": "127.0.0.1", "port": 65010, "redirect_path":
                "authorize_callback", "link_path": "oauth"}
        fileIO(f, "save", data)


def setup(bot):
    check_folder()
    check_file()
    if prawInstalled and o2uInstalled:
        n = Reddit(bot)
        bot.add_cog(n)
    elif prawInstalled and not o2uInstalled:
        raise RuntimeError("You need to do 'pip3 install praw-OAuth2Util'")
    elif o2uInstalled and not prawInstalled:
        raise RuntimeError("You need to do 'pip3 install praw'")
    else:
        raise RuntimeError("You need to do 'pip3 install praw praw-OAuth2Util'")
