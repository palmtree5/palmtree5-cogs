from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
import os
import discord
import asyncio


class NewsAnnouncer():
    """News announcer. Allows users to sign up to receive notifications
    by granting them a role. Anyone with certain permissions for a given
    channel can make announcements in that channel via command. Roles
    are based on the name of the channel and announcements are made
    in the channel whose role should receive the announcement."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/newsannouncer/settings.json")

    @checks.mod_or_permissions(manage_channels=True)
    @commands.command(pass_context=True)
    async def addnewschannel(self, ctx, channel_prefix: str=None):
        """Adds news functionality for a channel. Channel prefix is
        any part of the channel name that should not be included in
        the name of the role to be created for notifications"""
        channel = ctx.message.channel
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {}
        if channel.id not in self.settings[server.id]:
            self.settings[server.id][channel.id] = {}
        if channel_prefix:
            new_role_name = channel.name.replace(channel_prefix, "") +\
                " news"
        else:
            new_role_name = channel.name
        try:
            new_role = await self.bot.create_role(server, name=new_role_name,
                                                  permissions=discord.Permissions(permissions=0))
        except discord.Forbidden:
            await self.bot.say("I cannot create roles!")
            return
        except discord.HTTPException:
            await self.bot.say("Something went wrong!")
            return
        await self.bot.say("Role created!")
        self.settings[server.id][channel.id]["role_id"] = new_role.id
        self.settings[server.id][channel.id]["joined"] = []
        dataIO.save_json("data/newsannouncer/settings.json", self.settings)

    @checks.mod_or_permissions(manage_channels=True)
    @commands.command(pass_context=True)
    async def deletenewschannel(self, ctx, channel: discord.Channel):
        """Removes news functionality for a channel"""
        server = ctx.message.server
        if server.id not in self.settings:
            await self.bot.say("Nothing available for this server!")
            return
        if channel.id not in self.settings[server.id]:
            await self.bot.say("News functionality isn't set up for that channel!")
            return
        role = [r for r in ctx.message.server.roles if r.id == self.settings[server.id][channel.id]["role_id"]][0]
        try:
            await self.bot.delete_role(server, role)
        except discord.Forbidden:
            await self.bot.say("I cannot delete roles!")
            return
        except discord.HTTPException:
            await self.bot.say("Something went wrong!")
            return
        else:
            await self.bot.say("Role removed!")
            self.settings[server.id].pop(channel.id, None)
            dataIO.save_json("data/newsannouncer/settings.json", self.settings)

    @commands.command(pass_context=True)
    async def joinnews(self, ctx):
        """Joins the news role for the current channel"""
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id not in self.settings or\
                channel.id not in self.settings[server.id]:
            await self.bot.say("No news role available here!")
            return
        author = ctx.message.author
        if author.id in self.settings[server.id][channel.id]["joined"]:
            await self.bot.say("You already have the role for this channel!")
            return
        role_id = self.settings[server.id][channel.id]["role_id"]
        role_to_add = [r for r in server.roles if r.id == role_id][0]
        try:
            await self.bot.add_roles(author, role_to_add)
        except discord.Forbidden:
            await self.bot.say("I don't have permissions to add roles here!")
            return
        except discord.HTTPException:
            await self.bot.say("Something went wrong while doing that.")
            return
        await self.bot.say("Added that role successfully")
        self.settings[server.id][channel.id]["joined"].append(author.id)
        dataIO.save_json("data/newsannouncer/settings.json", self.settings)

    @commands.command(pass_context=True)
    async def leavenews(self, ctx):
        """Leaves the news role for the current channel"""
        server = ctx.message.server
        channel = ctx.message.channel
        author = ctx.message.author

        if server.id not in self.settings or\
                channel.id not in self.settings[server.id]:
            await self.bot.say("No news role available here!")
            return
        if author.id not in self.settings[server.id][channel.id]["joined"]:
            await self.bot.say("You don't have that role!")
            return

        role_id = self.settings[server.id][channel.id]["role_id"]
        role_to_remove = [r for r in server.roles if r.id == role_id][0]
        try:
            await self.bot.remove_roles(author, role_to_remove)
        except discord.Forbidden:
            await self.bot.say("I don't have permissions to remove roles here!")
            return
        except discord.HTTPException:
            await self.bot.say("Something went wrong while doing that.")
            return
        await self.bot.say("Removed that role successfully")
        self.settings[server.id][channel.id]["joined"].remove(author.id)
        dataIO.save_json("data/newsannouncer/settings.json", self.settings)

    @checks.mod_or_permissions(manage_channels=True)
    @commands.command(pass_context=True)
    async def makeannouncement(self, ctx, *, message: str):
        """Makes an announcement in the current channel"""
        server = ctx.message.server
        channel = ctx.message.channel
        role_id = self.settings[server.id][channel.id]["role_id"]
        role_to_edit = [r for r in server.roles if r.id == role_id][0]
        await self.bot.edit_role(server, role_to_edit, mentionable=True)
        asyncio.sleep(2.5)
        await self.bot.say(role_to_edit.mention + " " + message)
        asyncio.sleep(2)
        await self.bot.edit_role(server, role_to_edit, mentionable=False)


def check_folder():
    """Data folder validator"""
    if not os.path.isdir("data/newsannouncer"):
        print("Creating data/newsannouncer directory")
        os.mkdir("data/newsannouncer")


def check_file():
    """Data file validator"""
    data = {}
    if not dataIO.is_valid_json("data/newsannouncer/settings.json"):
        print("Creating settings.json for newsannouncer")
        dataIO.save_json("data/newsannouncer/settings.json", data)


def setup(bot):
    """Cog setup function"""
    check_folder()
    check_file()
    to_add = NewsAnnouncer(bot)
    bot.add_cog(to_add)
