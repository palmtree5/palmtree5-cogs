from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import discord
import tweepy as tw
import os
import datetime
import json
from __main__ import send_cmd_help

class Tweets():
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/tweets/settings.json'
        settings = fileIO(self.settings_file, 'load')
        if 'consumer_key' in list(settings.keys()):
            self.consumer_key = settings['consumer_key']
        if 'consumer_secret' in list(settings.keys()):
            self.consumer_secret = settings['consumer_secret']
        if 'access_token' in list(settings.keys()):
            self.access_token = settings['access_token']
        if 'access_secret' in list(settings.keys()):
            self.access_secret = settings['access_secret']

    def authenticate(self):
        auth = tw.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_secret)
        return tw.API(auth)
    @commands.group(pass_context=True, no_pm=True, name='tweets')
    async def _tweets(self, ctx):
        """Gets various information from Twitter's API"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_tweets.command(pass_context=True, no_pm=True, name='get')
    async def get_tweets(self, ctx, username):
        message = ""
        if username is not None:
            api = self.authenticate()
            message += "Last 5 tweets for " + username + ":\n\n"
            for status in tw.Cursor(api.user_timeline, id=username).items(5):
                message += status.text
                message += "\n"
        else:
            message = "No username specified!"
        await self.bot.say('```{}```'.format(message))

    @commands.group(pass_context=True, name='tweetset')
    @checks.is_owner()
    async def _tweetset(self, ctx):
        """Command for setting required access information for the API"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_tweetset.command(pass_context=True, name='consumerkey')
    @checks.is_owner()
    async def set_consumer_key(self, ctx, cons_key):
        message = ""
        if cons_key is not None:
            settings = fileIO(self.settings_file, 'load')
            settings["consumer_key"] = cons_key
            settings = fileIO(self.settings_file, 'save', settings)
            message = "Consumer key saved!"
        else:
            message = "No consumer key provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='consumersecret')
    @checks.is_owner()
    async def set_consumer_secret(self, ctx, cons_secret):
        message = ""
        if cons_secret is not None:
            settings = fileIO(self.settings_file, 'load')
            settings["consumer_secret"] = cons_secret
            settings = fileIO(self.settings_file, 'save', settings)
            message = "Consumer secret saved!"
        else:
            message = "No consumer secret provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='accesstoken')
    @checks.is_owner()
    async def set_access_token(self, ctx, token):
        message = ""
        if token is not None:
            settings = fileIO(self.settings_file, 'load')
            settings["access_token"] = token
            settings = fileIO(self.settings_file, 'save', settings)
            message = "Access token saved!"
        else:
            message = "No access token provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='accesssecret')
    @checks.is_owner()
    async def set_access_secret(self, ctx, secret):
        message = ""
        if secret is not None:
            settings = fileIO(self.settings_file, 'load')
            settings["access_secret"] = secret
            settings = fileIO(self.settings_file, 'save', settings)
            message = "Access secret saved!"
        else:
            message = "No access secret provided!"
        await self.bot.say('```{}```'.format(message))

def check_folder():
    if not os.path.exists("data/tweets"):
        print("Creating data/tweets folder")
        os.makedirs("data/tweets")

def check_file():
    data = {'consumer_key': '', 'consumer_secret': '', 'access_token': '', 'access_secret': ''}
    f = "data/tweets/settings.json"
    if not fileIO(f, "check"):
        print("Creating default settings.json...")
        fileIO(f, "save", data)

def setup(bot):
    check_folder()
    check_file()
    n = Tweets(bot)
    bot.add_cog(n)
