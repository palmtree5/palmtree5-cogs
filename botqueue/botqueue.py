"""Modification of the Autoapprove cog by https://github.com/tekulvw"""
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
import urllib.parse as up
import os
import json
import aiohttp
import discord
from datetime import datetime as dt


numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌",
    "approve": "✅"
}


class BotQueue:
    """A queue of requests to add bots to servers"""

    def __init__(self, bot):
        self.bot = bot
        self.base_api_url = "https://discordapp.com/api/oauth2/authorize?"
        self.enabled = dataIO.load_json('data/botqueue/enabled.json')
        self.session = aiohttp.ClientSession()

    def __unload(self):
        self.session.close()

    def save_enabled(self):
        dataIO.save_json('data/botqueue/enabled.json', self.enabled)

    @commands.group(no_pm=True, pass_context=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def botqueue(self, ctx):
        server = ctx.message.server
        channel = ctx.message.channel
        me = server.me
        if not channel.permissions_for(me).manage_messages:
            await self.bot.say("I don't have manage_messages permissions."
                               " I do not recommend submitting your "
                               "authorization key until I do.")
            return
        if not channel.permissions_for(me).manage_server:
            await self.bot.say("I do not have manage_server. This cog is "
                               "useless until I do.")
            return
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            return

    @botqueue.command(no_pm=True, pass_context=True, name="toggle")
    @checks.serverowner_or_permissions(manage_server=True)
    async def _botqueue_toggle(self, ctx):
        server = ctx.message.server
        if server.id not in self.enabled:
            await self.bot.say('BotQueue not set up for this server.')
        else:
            self.enabled[server.id]["ENABLED"] = \
                not self.enabled[server.id]["ENABLED"]
            self.save_enabled()
            if self.enabled[server.id]["ENABLED"]:
                await self.bot.say("BotQueue enabled.")
            else:
                await self.bot.say("BotQueue disabled.")

    @botqueue.command(no_pm=True, pass_context=True, name="check")
    @checks.serverowner_or_permissions(manage_server=True)
    async def _botqueue_check(self, ctx):
        """Checks the bot queue"""
        server = ctx.message.server
        if server.id not in self.enabled:
            await self.bot.say('BotQueue not set up for this server.')
            return
        elif not self.enabled[server.id]['ENABLED']:
            await self.bot.say('BotQueue not enabled for this server.')
            return
        if not self.enabled[server.id]["QUEUE"]:
            await self.bot.say('No bots in the queue!')
            return
        queue = self.enabled[server.id]["QUEUE"]
        post_list = []
        remove_list = []
        for request in queue:
            author = server.get_member(request["author"])
            if author is None:
                remove_list.append(request)
                continue
            bot_url = request["url"]
            author_tenure = author.joined_at
            requested_at = request["time"]
            now = dt.utcnow()
            delta = str(now - author_tenure)

            embed = discord.Embed(title="Bot join request", url=bot_url)
            embed.add_field(name="Requested by", value=author.mention, inline=False)
            embed.add_field(name="Requester in server for", value=delta)
            embed.set_footer(text="Requested at {}".format(requested_at))
            post_list.append((embed, request))
        if remove_list:
            for req in remove_list:
                queue.remove(req)
            self.enabled[server.id]["QUEUE"] = queue
            self.save_enabled()
        if post_list:
            await self.queue_menu(ctx, post_list, message=None, page=0, timeout=30)
        else:
            await self.bot.say("No requests to show!")

    @botqueue.command(no_pm=True, pass_context=True, name="setup")
    @checks.serverowner_or_permissions(manage_server=True)
    async def _botqueue_setup(self, ctx, authorization_key):
        """You will need to submit the user Authorization header key
            (can be found using dev tools in Chrome) of some user that will
            always have manage_server on this server."""
        server = ctx.message.server
        if server.id not in self.enabled:
            self.enabled[server.id] = {"ENABLED": False, "QUEUE": []}
        self.enabled[server.id]['KEY'] = authorization_key
        self.save_enabled()
        await self.bot.delete_message(ctx.message)
        await self.bot.say('Key saved. Deleted message for security.'
                           ' Use `botqueue toggle` to enable.')

    @commands.command(no_pm=True, pass_context=True)
    async def queuebot(self, ctx, oauth_url):
        """Requires your OAUTH2 URL to automatically approve your bot to
            join"""
        server = ctx.message.server
        if server.id not in self.enabled:
            await self.bot.say('BotQueue not set up for this server.'
                               ' Let the server owner know if you think it'
                               ' should be.')
            return
        elif not self.enabled[server.id]['ENABLED']:
            await self.bot.say('BotQueue not enabled for this server.'
                               ' Let the server owner know if you think it'
                               ' should be.')
            return

        queue = self.enabled[server.id]['QUEUE']
        author = ctx.message.author
        for entry in queue:
            if entry["author"] == author.id:
                await self.bot.say("You already have a request in the queue!")
                return
        new_request = {
            "author": author.id,
            "url": oauth_url,
            "time": str(ctx.message.timestamp)
        }
        queue.append(new_request)
        self.enabled[server.id]['QUEUE'] = queue
        self.save_enabled()
        await self.bot.say(
            "Your request has been added to the queue!\nYou will "
            "be notified when your request is approved or denied"
        )

    async def queue_menu(self, ctx, queue_list: list,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        cur_page = queue_list[page]
        emb = cur_page[0]
        request = cur_page[1]
        server = ctx.message.server
        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=emb)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")
            await self.bot.add_reaction(message, "✅")
            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=emb)
        react = await self.bot.wait_for_reaction(
            message=message, user=ctx.message.author, timeout=timeout,
            emoji=["➡", "⬅", "❌", "✅"]
        )
        if react is None:
            await self.bot.delete_message(message)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            next_page = 0
            if page == len(queue_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.queue_menu(ctx, queue_list, message=message,
                                         page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(queue_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.queue_menu(ctx, queue_list, message=message,
                                         page=next_page, timeout=timeout)
        elif react == "approve":
            oauth_url = request["url"]
            key = self.enabled[server.id]['KEY']
            parsed = up.urlparse(oauth_url)
            queryattrs = up.parse_qs(parsed.query)
            queryattrs['client_id'] = int(queryattrs['client_id'][0])
            queryattrs['scope'] = queryattrs['scope'][0]
            queryattrs.pop('permissions', None)
            full_url = self.base_api_url + up.urlencode(queryattrs)
            status = await self.get_bot_api_response(full_url, key, server.id)
            if status < 400:
                await self.bot.say("Succeeded!")
            else:
                await self.bot.say("Failed, error code {}. ".format(status))
            author = server.get_member(request["author"])
            await self.bot.send_message(
                author,
                "Your bot was added to {}!".format(server.name)
            )
            for req in self.enabled[server.id]["QUEUE"]:
                if req == request:
                    self.enabled[server.id]["QUEUE"].remove(req)
                    self.save_enabled()
                    break
            await self.bot.delete_message(message)

        else:
            author = server.get_member(request["author"])
            await self.bot.send_message(
                author,
                "Sorry, your request to add a bot to {} was denied".format(server.name)
            )
            for req in self.enabled[server.id]["QUEUE"]:
                if req == request:
                    self.enabled[server.id]["QUEUE"].remove(req)
                    self.save_enabled()
                    break
            await self.bot.say("That request has been denied")
            await self.bot.delete_message(message)

    async def get_bot_api_response(self, url, key, serverid):
        data = {"guild_id": serverid, "permissions": 0, "authorize": True}
        data = json.dumps(data).encode('utf-8')
        headers = {'authorization': key, 'content-type': 'application/json'}
        async with self.session.post(url, data=data, headers=headers) as r:
            status = r.status
        return status


def check_folder():
    if not os.path.exists("data/botqueue"):
        print("Creating data/botqueue folder...")
        os.makedirs("data/botqueue")


def check_file():
    enabled = {}

    f = "data/botqueue/enabled.json"
    if not dataIO.is_valid_json(f):
        print("Creating default botqueue's enabled.json...")
        dataIO.save_json(f, enabled)


def setup(bot):
    check_folder()
    check_file()
    n = BotQueue(bot)
    bot.add_cog(n)
