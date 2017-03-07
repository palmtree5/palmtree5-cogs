from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
from datetime import datetime as dt
import asyncio
import discord
import os
import calendar


class EventMaker():
    """A tool for creating events inside of Discord. 
    Anyone can create an event by default. If a specific role has been specified, users must have that role,
    the server's mod or admin role, or be the server owner to create events. Reminders will be posted to the
    configured channel (default: the server's default channel), as well as direct messaged to everyone who has signed up"""
    def __init__(self, bot):
        self.bot = bot
        self.events = dataIO.load_json(os.path.join("data", "eventmaker", "events.json"))
        self.settings = dataIO.load_json(os.path.join("data", "eventmaker", "settings.json"))

    @commands.command(pass_context=True)
    async def eventcreate(self, ctx):
        """Wizard-style event creation tool. The event will only be created if
        all information is provided properly
        """
        author = ctx.message.author
        server = ctx.message.server
        allowed_roles = []
        server_owner = server.owner
        if self.settings[server.id]["role"] is not None:
            specified_role = [r for r in server.roles if r.id == self.settings[server.id]["role"]][0]
            allowed_roles.append(specified_role)
            allowed_roles.append(self.bot.settings.get_server_mod(server))
            allowed_roles.append(self.bot.settings.get_server_admin(server))

        if len(allowed_roles) > 0 and author != server_owner:
            for role in author.roles:
                if role in allowed_roles:
                    break
            else:
                await self.bot.say("You don't have permission to create events!")
                return

        creation_time = dt.utcnow()
        await self.bot.say("Enter a name for the event: ")
        msg = await self.bot.wait_for_message(author=author, timeout=30)
        if msg is None:
            await self.bot.say("No name provided!")
            return
        name = msg.content
        msg = None
        await self.bot.say("Enter the amount of time from now the event will take place (ex. 1w, 3d 12h, 1y 2w 4d 12h 30m): ")
        msg = await self.bot.wait_for_message(author=author, timeout=30)
        if msg is None:
            await self.bot.say("No start time provided!")
            return
        start_time = self.parse_time(creation_time, msg)
        if start_time is None:
            await self.bot.say("Something went wrong with parsing the time you entered!")
            return
        msg = None
        await self.bot.say("Enter a description for the event: ")
        msg = await self.bot.wait_for_message(author=author, timeout=30)
        if msg is None:
            await self.bot.say("No description provided!")
            return
        if len(msg.content) > 750:
            await self.bot.say("Your description is too long!")
            return
        else:
            desc = msg.content

        if server.id not in self.events:
            self.events[server.id] = []
            self.settings[server.id]["next_id"] = 1
        new_event = {
            "id": self.settings[server.id]["next_id"],
            "creator": author.id,
            "create_time": calendar.timegm(creation_time.utctimetuple()),
            "event_name": name,
            "event_start_time": start_time,
            "description": desc,
            "has_started": False,
            "participants": [author.id]
        }
        self.settings[server.id]["next_id"] += 1
        self.events[server.id].append(new_event)
        dataIO.save_json(os.path.join("data", "eventmaker", "settings.json"), self.settings)
        dataIO.save_json(os.path.join("data", "eventmaker", "events.json"), self.events)
        emb = discord.Embed(title=new_event["event_name"],
                            description=new_event["description"])
        emb.add_field(name="Created by",
                      value=discord.utils.get(
                          self.bot.get_all_members(),
                          id=new_event["creator"]))
        emb.set_footer(text="Created at " + dt.utcfromtimestamp(new_event["create_time"]).strftime("%Y-%m-%d %H:%M:%S"))
        emb.add_field(name="Event ID", value=str(new_event["id"]))
        emb.add_field(name="Participant count", value=str(len(new_event["participants"])))
        emb.add_field(name="Start time", value=dt.utcfromtimestamp(new_event["event_start_time"]))
        await self.bot.say(embed=emb)

    @commands.command(pass_context=True)
    async def joinevent(self, ctx, event_id: int):
        """Join the specified event"""
        server = ctx.message.server
        for event in self.events[server.id]:
            if event["id"] == event_id:
                if event["has_started"] == False:
                    if ctx.message.author.id not in event["participants"]:
                        event["participants"].append(ctx.message.author.id)
                        await self.bot.say("Joined the event!")
                        dataIO.save_json(os.path.join("data", "eventmaker", "events.json"), self.events)
                    else:
                        await self.bot.say("You have already joined that event!")
                else:
                    await self.bot.say("That event has already started!")
                break
    
    def parse_time(self, cur_time, msg: discord.Message):
        """Parse the time"""
        start_time = calendar.timegm(cur_time.utctimetuple())
        content = msg.content
        pieces = content.split()
        for piece in pieces:
            if piece.endswith("y"):
                try:
                    start_time += int(piece[:-1]) * 31536000 # number of seconds in a year
                except ValueError:
                    return None # issue with the user's input
            elif piece.endswith("w"):
                try:
                    start_time += int(piece[:-1]) * 604800 # number of seconds in a week
                except ValueError:
                    return None # issue with the user's input
            elif piece.endswith("d"):
                try:
                    start_time += int(piece[:-1]) * 86400 # number of seconds in a day
                except ValueError:
                    return None # issue with the user's input
            elif piece.endswith("h"):
                try:
                    start_time += int(piece[:-1]) * 3600 # number of seconds in an hour
                except ValueError:
                    return None # issue with the user's input
            elif piece.endswith("m"):
                try:
                    start_time += int(piece[:-1]) * 60 # number of seconds in a minute
                except ValueError:
                    return None # issue with the user's input
            elif piece.endswith("s"):
                try:
                    start_time += int(piece[:-1]) * 1 # number of seconds in a second
                except ValueError:
                    return None # issue with the user's input
            else:
                return None # something went wrong as a result of the user's input
            return start_time

    @commands.group(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def eventset(self, ctx):
        """Event maker settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @eventset.command(pass_context=True, name="channel")
    @checks.admin_or_permissions(manage_server=True)
    async def eventset_channel(self, ctx, channel: discord.Channel):
        """Set the channel used for creating announcements and displaying reminders
        Make sure users who should be able to create events can send messages
        in this channel"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {}
            self.settings[server.id]["role"] = None
            self.settings[server.id]["next_id"] = 1
        self.settings[server.id]["channel"] = channel.id
        dataIO.save_json(os.path.join("data", "eventmaker", "settings.json"), self.settings)
        await self.bot.say("Channel set to {}".format(channel.mention))

    @eventset.command(pass_context=True, name="role")
    @checks.admin_or_permissions(manage_server=True)
    async def eventset_role(self, ctx, *, role: str=None):
        """Set the role allowed to create events. Default is for everyone to be able to create events"""
        server = ctx.message.server
        if role is not None:
            role_obj = [r for r in server.roles if r.name == role][0]
            if server.id not in self.settings:
                self.settings[server.id] = {}
                self.settings[server.id]["next_id"] = 1
                self.settings[server.id]["channel"] = server.id
            self.settings[server.id]["role"] = role_obj.id
            dataIO.save_json(os.path.join("data", "eventmaker", "settings.json"), self.settings)
            await self.bot.say("Channel set to {}".format(role))
        else:
            if server.id not in self.settings:
                self.settings[server.id] = {}
                self.settings[server.id]["next_id"] = 1
                self.settings[server.id]["channel"] = server.id
            self.settings[server.id]["role"] = None
            dataIO.save_json(os.path.join("data", "eventmaker", "settings.json"), self.settings)
            await self.bot.say("Role unset!")

    async def check_events(self):
        """Event loop"""
        CHECK_DELAY = 60
        while self == self.bot.get_cog("EventMaker"):
            cur_time = dt.utcnow()
            cur_time = calendar.timegm(cur_time.utctimetuple())
            save = False
            for server in list(self.events.keys()):
                channel = discord.utils.get(self.bot.get_all_channels(),
                                            id=self.settings[server]["channel"])
                for event in self.events[server]:
                    if cur_time >= event["event_start_time"]\
                            and not event["has_started"]:
                        emb = discord.Embed(title=event["event_name"],
                                            description=event["description"])
                        emb.add_field(name="Created by",
                                      value=discord.utils.get(
                                          self.bot.get_all_members(),
                                          id=event["creator"]))
                        emb.set_footer(text="Created at " + dt.utcfromtimestamp(event["create_time"]).strftime("%Y-%m-%d %H:%M:%S"))
                        emb.add_field(name="Event ID", value=str(event["id"]))
                        emb.add_field(name="Participant count", value=str(len(event["participants"])))
                        await self.bot.send_message(channel, embed=emb)
                        for user in event["participants"]:
                            target = discord.utils.get(self.bot.get_all_members(), id=user)
                            await self.bot.send_message(target, embed=emb)
                        event["has_started"] = True
                        save = True
            if save:
                dataIO.save_json(os.path.join("data", "eventmaker", "events.json"), self.events)
            await asyncio.sleep(CHECK_DELAY)


def check_folder():
    if not os.path.isdir(os.path.join("data", "eventmaker")):
        print("Creating the eventmaker directory in data")
        os.mkdir(os.path.join("data", "eventmaker"))


def check_file():
    if not dataIO.is_valid_json(os.path.join("data", "eventmaker", "events.json")):
        dataIO.save_json(os.path.join("data", "eventmaker", "events.json"), {})
    if not dataIO.is_valid_json(os.path.join("data", "eventmaker", "settings.json")):
        dataIO.save_json(os.path.join("data", "eventmaker", "settings.json"), {})


def setup(bot):
    check_folder()
    check_file()
    n = EventMaker(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.check_events())
    bot.add_cog(n)
