from discord.ext import commands
import discord
from .utils import checks
from .utils.dataIO import dataIO
import os
import asyncio


class BanRole():
    """Allows banning and unbanning users by role"""
    def __init__(self, bot):
        self.bot = bot
        self.fp = os.path.join("data", "banrole", "bans.json")
        self.banlist = dataIO.load_json(self.fp)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def banrole(self, ctx, *, role: str):
        """Bans all members with the specified role.
        Make sure the bot's role is higher in the role
        hierarchy than the role you want it to ban"""
        server = ctx.message.server
        roles = [r for r in server.roles if r.name == role]
        if len(roles) == 0:
            await self.bot.say("That role doesn't exist!")
            return
        members_to_ban = [m for m in server.members if roles[0] in m.roles]
        ban_count = 0
        total_count = len(members_to_ban)
        msg = await self.bot.say("{}/{} members banned".format(ban_count, total_count))
        for member in members_to_ban:
            try:
                await self.bot.ban(member)
            except discord.Forbidden:
                await self.bot.say("I'm not allowed to do that.")
                return
            except Exception as e:
                print(e)
                await self.bot.say("An error occured. Check your console or logs for details")
                return
            else:
                ban_count += 1
                msg = await self.bot.edit_message(msg, "{}/{} members banned".format(ban_count, total_count))
                if roles[0].id not in self.banlist[server.id]:
                    self.banlist[server.id][roles[0].id] = []
                self.banlist[server.id][roles[0].id].append(member.id)
        dataIO.save_json(self.fp, self.banlist)
        await self.bot.say("Done banning members")
    
    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def unbanrole(self, ctx, *, role: str):
        """Unbans all users who had the specified role when
        they were banned"""
        server = ctx.message.server
        roles = [r for r in server.roles if r.name == role]
        if len(roles) == 0:
            await self.bot.say("That role doesn't exist!")
            return
        if roles[0].id not in self.banlist[server.id]:
            await self.bot.say("That role is not in the list!")
            return
        members_to_unban = self.banlist[server.id][roles[0].id]
        if len(members_to_unban) == 0:
            await self.bot.say("Nothing to do here!")
            return
        unbanned_count = 0
        total_unbans = len(members_to_unban)
        msg = await self.bot.say("{}/{} members unbanned.".format(unbanned_count, total_unbans))
        for member in members_to_unban:
            unbanned_count += 1
            await self.bot.http.unban(member, server.id)
            msg = await self.bot.edit_message(msg, "{}/{} members unbanned".format(unbanned_count, total_unbans))
        self.banlist[server.id][role] = []
        await self.bot.say("Done unbanning.")
        dataIO.save_json(self.fp, self.banlist)

    async def server_data_check(self):
        """Check that all servers the bot is in have data
        Only runs on cog load"""
        for server in self.bot.servers:
            if server.id not in self.banlist:
                self.banlist[server.id] = {}
        dataIO.save_json(self.fp, self.banlist)

    async def server_join(self, server):
        if server.id not in self.banlist:
            self.banlist[server.id] = {}
        dataIO.save_json(self.fp, self.banlist)


def check_folder():
    if not os.path.isdir(os.path.join("data", "banrole")):
        os.mkdir(os.path.join("data", "banrole"))


def check_file():
    if not dataIO.is_valid_json(os.path.join("data", "banrole", "bans.json")):
        dataIO.save_json(os.path.join("data", "banrole", "bans.json"), {})


def setup(bot):
    check_folder()
    check_file()
    n = BanRole(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.server_data_check())
    bot.add_listener(n.server_join, "on_server_join")
    bot.add_cog(n)
