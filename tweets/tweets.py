from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
try:
    import tweepy as tw
    twInstalled = True
except:
    twInstalled = False
import os
from __main__ import send_cmd_help


class TweetListener(tw.StreamListener):

    def on_status(self, status):
        message = status.user.name + ": " + status.text
        return message


class Tweets():

    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/tweets/settings.json'
        settings = dataIO.load_json(settings_file)
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

    @_tweets.command(pass_context=True, no_pm=True, name='getuser')
    async def get_user(self, ctx, username: str):
        """Get info about the specified user"""
        message = ""
        if username is not None:
            api = self.authenticate()
            user = api.get_user(username)
            message += "Info for " + user.screen_name + ":\n"
            message += "Followers: " + str(user.followers_count) + "\n"
            message += "Friends: " + str(user.friends_count)
        else:
            message = "Uh oh, an error occurred somewhere!"
        await self.bot.say("```{}```".format(message))

    @_tweets.command(pass_context=True, no_pm=True, name='gettweets')
    async def get_tweets(self, ctx, username: str, count: int):
        """Gets the specified number of tweets for the specified username"""
        cnt = count
        if count > 25:
            cnt = 25
        message = ""

        if username is not None:
            if cnt < 1:
                await self.bot.say("I can't do that, silly! Please specify a \
                    number greater than or equal to 1")
                return

            api = self.authenticate()
            if cnt == 1:
                message += "Last tweet for " + username + ":\n\n"
            else:
                message += "Last " + str(cnt) + " tweets for " + \
                    username + ":\n\n"
            try:
                for status in tw.Cursor(api.user_timeline, id=username).items(cnt):
                    message += status.text
                    message += "\n\n"
            except tw.TweepError as e:
                await self.bot.say("Whoops! Something went wrong here. \
                    The error code is " + str(e))
                return
        else:
            await self.bot.say("No username specified!")
            return
        await self.bot.say('```{}```'.format(message))


    @commands.group(pass_context=True, name='tweetset')
    @checks.admin_or_permissions(manage_server=True)
    async def _tweetset(self, ctx):
        """Command for setting required access information for the API"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_tweetset.group(pass_context=True, hidden=True, name="stream")
    @checks.admin_or_permissions(manage_server=True)
    async def _stream(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)


    @_stream.group(pass_context=True, hidden=True, name="term")
    @checks.admin_or_permissions(manage_server=True)
    async def _term(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)


    @_term.command(pass_context=True, hidden=True, name="add")
    @checks.admin_or_permissions(manage_server=True)
    async def _add(self, ctx, term_to_track):
        if term_to_track is None:
            await self.bot.say("I can't do that, silly!")
        else:
            settings = fileIO(self.settings_file, "load")
            if ctx.message.server in settings:
                cur_terms = settings["servers"][ctx.message.server]["terms"]
                cur_terms.append(term_to_track)
                settings["servers"][ctx.message.server]["terms"] = cur_terms
            else:
                cur_terms = []
                cur_terms.append(term_to_track)
                settings["servers"] = {}
                settings["servers"][ctx.message.server] = {}
                settings["servers"][ctx.message.server]["terms"] = cur_terms
            fileIO(self.settings_file, "save", settings)
            await self.bot.say("Added the requested term!")


    @_term.command(pass_context=True, hidden=True, name="remove")
    @checks.admin_or_permissions(manage_server=True)
    async def _remove(self, ctx, term_to_remove):
        settings = fileIO(self.settings_file, "load")
        if term_to_remove is None:
            await self.bot.say("You didn't specify a term to remove!")
        elif term_to_remove == "all":
            settings["servers"][ctx.message.server]["terms"] = []
            fileIO(self.settings_file, "save", settings)
            await self.bot.say("Cleared the tracking list!")
        else:
            cur_list = settings["servers"][ctx.message.server]["terms"]
            cur_list.remove(term_to_remove)
            settings["servers"][ctx.message.server]["terms"] = cur_list
            fileIO(self.settings_file, "save", settings)
            await self.bot.say("Removed the specified term!")


    @_tweetset.command(pass_context=True, name='consumerkey')
    @checks.is_owner()
    async def set_consumer_key(self, ctx, cons_key):
        message = ""
        if cons_key is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["consumer_key"] = cons_key
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Consumer key saved!"
        else:
            message = "No consumer key provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='consumersecret')
    @checks.is_owner()
    async def set_consumer_secret(self, ctx, cons_secret):
        message = ""
        if cons_secret is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["consumer_secret"] = cons_secret
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Consumer secret saved!"
        else:
            message = "No consumer secret provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='accesstoken')
    @checks.is_owner()
    async def set_access_token(self, ctx, token):
        message = ""
        if token is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["access_token"] = token
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Access token saved!"
        else:
            message = "No access token provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='accesssecret')
    @checks.is_owner()
    async def set_access_secret(self, ctx, secret):
        message = ""
        if secret is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["access_secret"] = secret
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Access secret saved!"
        else:
            message = "No access secret provided!"
        await self.bot.say('```{}```'.format(message))

def check_folder():
    if not os.path.exists("data/tweets"):
        print("Creating data/tweets folder")
        os.makedirs("data/tweets")

def check_file():
    data = {'consumer_key': '', 'consumer_secret': '', \
        'access_token': '', 'access_secret': ''}
    f = "data/tweets/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default settings.json...")
        dataIO.save_json(f, data)

def setup(bot):
    check_folder()
    check_file()
    if twInstalled:
        n = Tweets(bot)
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to do 'pip3 install tweepy'")
