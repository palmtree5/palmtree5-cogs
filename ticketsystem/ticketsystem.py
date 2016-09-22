import discord
from discord.ext import commands
from .utils import checks
from __main__ import send_cmd_help
from .utils.dataIO import fileIO
import os


class TicketSystem():

    def __init__(self, bot):
        self.bot = bot
        self.settingsfile = "data/ticketsystem/settings.json"
        self.ticketsfile = "data/ticketsystem/tickets.json"
        self.settings = fileIO(self.settingsfile, "load")
        self.tickets = fileIO(self.ticketsfile, "load")

    def create_server(self, server_id):
        default_server_settings = {
            "enabled": True,
            "mod_ticket_channel": "mods",
            "admin_ticket_channel": "admins",
            "mod_categories": [],
            "admin_categories": []
        }
        default_tickets = {
            "tickets": []
        }
        self.settings[str(server_id)] = default_server_settings
        fileIO("data/ticketsystem/settings.json", "save", self.settings)
        self.tickets[str(server_id)] = default_tickets
        fileIO("data/ticketsystem/tickets.json", "save", self.tickets)

    @commands.group(pass_context=True, name="ticket")
    async def _ticket(self, ctx):
        """Commands for normal users to work with tickets"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_ticket.command(pass_context=True, name="open")
    async def _open(self, ctx):
        if ctx.message.channel.is_private:
            await self.bot.say("Try opening your ticket in a server!")
            return
        else:
            if ctx.message.server.id not in self.tickets:
                await self.bot.say("The server owner has not set up the ticket system for this server!")
                return
            server = ctx.message.server
            author = ctx.message.author
            categories = settings[server.id]["categories"]
            categories_str = ""
            for cat in categories:
                categories_str = categories_str + cat + ", "
            await self.bot.send_message(author, "You have requested to open a ticket. We will now proceed with that process.")
            await self.bot.send_message(author, "Please enter a title for your ticket: ")
            title = await self.bot.wait_for_message(timeout=15, author=author)
            if title is None:
                await self.bot.send_message(author, "No input received. Ticket request cancelled")
                return

            await self.bot.send_message("Enter a category. Valid categories for this server are: " + categories_str[:-2])
            selected_cat = await self.bot.wait_for_message(timeout=15, author=author)

            if selected_cat is None:
                await self.bot.send_message(author, "No input received. Ticket request cancelled")
                return
            elif selected_cat not in categories:
                await self.bot.send_message(author, "That is not a valid category. Cancelling request")
                return

            await self.bot.send_message("Please describe your issue in less than 2000 characters: ")
            issue_desc = await self.bot.wait_for_message(timeout=15, author=author)

            if issue_desc is None:
                await self.bot.send_message(author, "No input received. Ticket request cancelled")
                return

            new_ticket = {"title": title, "author": author.name, "category": selected_cat, "description": issue_desc, "open": True}
            self.tickets[str(server.id)]["tickets"].append(new_ticket)
            fileIO(self.ticketsfile, "save", self.tickets)

    @checks.serverowner_or_permissions(administrator=True)
    @commands.group(pass_context=True, name="ticketset")
    async def _ticketset(self, ctx):
        """Settings for the ticket system"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @checks.serverowner_or_permissions(administrator=True)
    @_ticketset.group(pass_context=True, name="catset")
    async def _catset(self, ctx):
        """Category commands for a server"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @checks.serverowner_or_permissions(administrator=True)
    @_catset.group(pass_context=True, name="addcat")
    async def _addcat(self, ctx):
        """Commands for adding a category"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @checks.serverowner_or_permissions(administrator=True)
    @_addcat.command(pass_context=True, no_pm=True, name="mod")
    async def add_mod_cat(self, ctx, category_name):
        """Add a mod category"""
        if ctx.message.server.id not in self.settings:
            await self.bot.say("The server owner has not set up the ticket system for this server!")
        else:
            await self.bot.say("Adding mod category " + category_name)
            self.settings[str(ctx.message.server.id)]["mod_categories"].append(category_name)
            fileIO(self.settingsfile, "save", self.settings)
            await self.bot.say("Added mod category!")

    @checks.serverowner_or_permissions(administrator=True)
    @_addcat.command(pass_context=True, no_pm=True, name="admin")
    async def add_admin_cat(self, ctx, category_name):
        """Add an admin category"""
        if ctx.message.server.id not in self.settings:
            await self.bot.say("The server owner has not set up the ticket system for this server!")
        else:
            await self.bot.say("Adding admin category " + category_name)
            self.settings[str(ctx.message.server.id)]["admin_categories"].append(category_name)
            fileIO(self.settingsfile, "save", self.settings)
            await self.bot.say("Added admin category!")

    @checks.serverowner_or_permissions(administrator=True)
    @_ticketset.command(pass_context=True, no_pm=True, name="initialize")
    async def _initialize(self, ctx):
        """Initialize ticket system for a server"""
        server_id = ctx.message.server.id
        await self.bot.say("Initializing ticket system for this server")
        self.create_server(server_id)
        await self.bot.say("Server initialized! Please see !ticketset catset for info on setting categories")

    @checks.serverowner_or_permissions(administrator=True)
    @_ticketset.command(pass_context=True, no_pm=True, name="modchannel")
    async def set_mod_channel(self, ctx, channel : discord.Channel):
        """Set the mod ticket channel"""
        server_id = ctx.message.server.id
        await self.bot.say("Setting mod channel")
        self.settings[str(server_id)]["mod_ticket_channel"] = channel.name
        fileIO(self.settingsfile, "save", self.settings)
        await self.bot.say("Set the mod channel!")

    @checks.serverowner_or_permissions(administrator=True)
    @_ticketset.command(pass_context=True, no_pm=True, name="adminchannel")
    async def set_admin_channel(self, ctx, channel : discord.Channel):
        """Set the admin ticket channel"""
        server_id = ctx.message.server.id
        await self.bot.say("Setting admin channel")
        self.settings[str(server_id)]["admin_ticket_channel"] = channel.name
        fileIO(self.settingsfile, "save", self.settings)
        await self.bot.say("Set the admin channel!")

def check_folder():
    if not os.path.exists("data/ticketsystem"):
        print("Creating data/ticketsystem folder")
        os.makedirs("data/ticketsystem")


def check_file():
    f = "data/ticketsystem/settings.json"
    data = {}
    if not fileIO(f, "check"):
        print("Creating default settings.json...")
        fileIO(f, "save", data)
    tickets_f = "data/ticketsystem/tickets.json"
    if not fileIO(tickets_f, "check"):
        print("Creating default tickets.json...")
        fileIO(tickets_f, "save", data)

def setup(bot):
    check_folder()
    check_file()
    n = TicketSystem(bot)
    bot.add_cog(n)
