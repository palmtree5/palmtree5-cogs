from discord.ext import commands
from .utils import checks
import discord
import praw
import OAuth2Util as o2u
import datetime as dt
import os
import configparser as c
from __main__ import send_cmd_help
import logging
log = logging.getLogger('red.reddit')


class RedReddit():

    def __init__(self, bot):
        self.bot = bot
        self.r = praw.Reddit("RedBotRedditCog/v0.1 by /u/palmtree5")
        self.o = o2u.OAuth2Util(self.r)
        self.o.refresh(force=True)

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
        for submission in self.r.get_subreddit(subreddit, fetch=True).get_new(limit=count):
            message += submission.title + ":      https://redd.it" +\
                submission.id + "\n"
        await self.bot.say('```{}```'.format(message))

    @_posts.command(pass_context=True, no_pm=True, name="hot")
    async def hot_posts(self, ctx, subreddit, count: int=1):
        """Get the specified number of posts from the specified subreddit,
        sorted by hot"""
        message = "The " + str(count) + " hottest posts for /r/" + subreddit\
            + "\n\n"
        for submission in self.r.get_subreddit(subreddit, fetch=True).get_hot(limit=count):
            message += submission.title + ":      https://redd.it" +\
                submission.id + "\n"
        await self.bot.say('```{}```'.format(message))


def check_folder():
    if not os.path.exists("data/reddit"):
        log.info("Creating data/reddit folder")
        os.makedirs("data/reddit")


def check_file():
    f = "data/reddit/oauth.ini"
    if not os.path.isfile(f):
        log.info("Creating default oauth.ini...")
        config = c.ConfigParser()
        config['app'] = \
            {'scope': 'read', 'refreshable': True, 'app_key': '',
                'app_secret': ''}
        config['server'] = \
            {'server_mode': False, 'url': '127.0.0.1',
                'port': 65010, 'redirect_path': 'authorize_callback',
                'link_path': 'oauth'}
        with open(f, "w") as cfg:
            config.write(cfg)
    f2 = "data/reddit/settings.json"
    data = {"UserAgent": "PalmBot:RedBotRedditCog:v0.5 (by /u/palmtree5)"}


def setup(bot):
    check_folder()
    check_file()
    n = RedReddit(bot)
    bot.add_cog(n)
