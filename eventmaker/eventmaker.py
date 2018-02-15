import asyncio
from datetime import datetime as dt

import discord
from discord.ext import commands
from redbot.core import Config, RedContext, checks
from redbot.core.utils.chat_formatting import pagify

from .helpers import parse_time, allowed_to_create

numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


class EventMaker:
    """A tool for creating events inside of Discord. Anyone can
    create an event by default. If a specific role has been
    specified, users must have that role, the server's mod or
    admin role, or be the server owner to create events. Reminders
    will be posted to the configured channel (default: the server's
    default channel), as well as direct messaged to
    everyone who has signed up"""

    default_guild = {
        "events": [],
        "min_role": 0,
        "next_available_id": 1
    }

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_guild(**self.default_guild)

    async def event_menu(self, ctx, event_list: list,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        emb = event_list[page]
        if not message:
            message = await ctx.send(embed=emb)
            await message.add_reaction("⬅")
            await message.add_reaction("❌")
            await message.add_reaction("➡")
        else:
            await message.edit(embed=emb)
        
        def react_check(r, u):
            return u == ctx.author and str(r.emoji) in ["➡", "⬅", "❌"]
        
        try:
            react = await self.bot.wait_for(
                "message", check=react_check, timeout=timeout
            )
        except asyncio.TimeoutError:
            try:
                await message.clear_reactions()
            except discord.Forbidden:  # cannot remove all reactions
                await message.remove_reaction("⬅", ctx.guild.me)
                await message.remove_reaction("❌", ctx.guild.me)
                await message.remove_reaction("➡", ctx.guild.me)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("➡", ctx.author)
                except discord.NotFound:
                    pass
            if page == len(event_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.event_menu(ctx, event_list, message=message,
                                         page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            perms = message.channel.permissions_for(ctx.guild.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                try:
                    await message.remove_reaction("⬅", ctx.author)
                except discord.NotFound:
                    pass
            if page == 0:
                next_page = len(event_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.event_menu(ctx, event_list, message=message,
                                         page=next_page, timeout=timeout)
        else:
            return await message.delete()

    @commands.group()
    async def event(self, ctx: RedContext):
        """Base command for events"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @event.command(name="create")
    async def event_create(self, ctx: RedContext):
        """Wizard-style event creation tool. The event will only be created if
        all information is provided properly. If a minimum required role has
        been set, users must have that role or higher, be in the mod/admin role, 
        or be the guild owner in order to use this command
        """
        author = ctx.author
        guild = ctx.guild

        event_id = await self.settings.guild(guild).next_available_id()
        min_role_id = await self.settings.guild(guild).min_role
        if min_role_id == 0:
            min_role = guild.default_role
        else:
            min_role = discord.utils.get(guild.roles, id=min_role_id)
        if not await allowed_to_create(ctx.bot, author, min_role, guild):
            await ctx.send("You aren't allowed to create events!")
            return

        creation_time = dt.utcnow().timestamp()
        await ctx.send("Enter a name for the event: ")
        
        def same_author_check(msg):
            return msg.author == author
        
        try:
            msg = await self.bot.wait_for("message", check=same_author_check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("No name provided!")
            return
        name = msg.content
        msg = None
        await ctx.send(
            "Enter the amount of time from now the event will take "
            "place (valid units are w, d, h, m, s): "
        )
        try:
            msg = await self.bot.wait_for("message", check=same_author_check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("No start time provided!")
            return
        start_time = parse_time(creation_time, msg)
        if start_time is None:
            await ctx.send("Something went wrong with parsing the time you entered!")
            return
        msg = None
        await ctx.send("Enter a description for the event: ")
        try:
            msg = await self.bot.wait_for("message", check=same_author_check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("No description provided!")
            return
        if len(msg.content) > 1500:
            await ctx.send("Your description is too long!")
            return
        else:
            desc = msg.content

        new_event = {
            "id": event_id,
            "creator": author.id,
            "create_time": creation_time,
            "event_name": name,
            "event_start_time": start_time,
            "description": desc,
            "has_started": False,
            "participants": [author.id]
        }
        async with self.settings.guild(guild).events() as event_list:
            event_list.append(new_event)
            event_list.sort(key=lambda x: x["create_time"])
        emb = discord.Embed(title=new_event["event_name"],
                            description=new_event["description"],
                            url="https://time.is/UTC",
                            timestamp=dt.utcfromtimestamp(new_event["create_time"]))
        emb.set_author(name=author.name, icon_url=author.avatar_url)
        emb.add_field(
            name="Start time (UTC)", value=str(dt.utcfromtimestamp(
                new_event["id"])))
        emb.add_field(name="Started", value="Yes" if new_event["has_started"] else "No")
        emb.add_field(name="Participants", value=str(len(new_event["participants"])))
        await ctx.send(embed=emb)

    @event.command(name="join")
    async def event_join(self, ctx: RedContext, event_id: int):
        """Join an event"""
        guild = ctx.guild
        to_join = None
        async with self.settings.guild(guild).events() as event_list:
            counter = 0
            for event in event_list:
                if event["id"] == event_id:
                    to_join = event
                    event_list.remove(event)
                    break
            
            if not to_join["has_started"]:
                if ctx.author.id not in event["participants"]:
                    to_join["participants"].append(ctx.author.id)
                    await ctx.send("Joined the event!")
                    event_list.append(to_join)
                    event_list.sort(key=lambda x: x["id"])
                else:
                    await ctx.send("You have already joined that event!")

    @event.command(name="leave")
    async def event_leave(self, ctx: RedContext, event_id: int):
        """Leave the specified event"""
        guild = ctx.guild
        to_leave = None
        async with self.settings.guild(guild).events() as event_list:
            counter = 0
            for event in event_list:
                if event["id"] == event_id:
                    to_leave = event
                    event_list.remove(event)
                    break
            
            if not to_leave["has_started"]:
                if ctx.author.id in to_leave["participants"]:
                    to_leave["participants"].remove(ctx.author.id)
                    await ctx.send("Left the event!")
                    event_list.append(to_leave)
                    event_list.sort(key=lambda x: x["id"])
                else:
                    await ctx.send("You are not part of that event!")

    @event.command(name="list")
    async def event_list(self, ctx: RedContext):
        """List events for this server that have not started yet"""
        guild = ctx.guild
        events = []
        async with self.settings.guild(guild).events() as event_list:
            for event in event_list:
                if not event["has_started"]:
                    emb = discord.Embed(title=event["event_name"],
                                        description=event["description"],
                                        url="https://time.is/UTC")
                    emb.add_field(name="Created by",
                                value=discord.utils.get(
                                    self.bot.get_all_members(),
                                    id=event["creator"]))
                    emb.set_footer(
                        text="Created at (UTC) " + dt.utcfromtimestamp(
                            event["create_time"]).strftime("%Y-%m-%d %H:%M:%S"))
                    emb.add_field(name="Event ID", value=str(event["id"]))
                    emb.add_field(
                        name="Participant count", value=str(
                            len(event["participants"])))
                    emb.add_field(
                        name="Start time (UTC)", value=dt.utcfromtimestamp(
                            event["event_start_time"]))
                    events.append(emb)
        if len(events) == 0:
            await ctx.send("No events available to join!")
        else:
            await self.event_menu(ctx, events, message=None, page=0, timeout=30)

    @event.command(name="who")
    async def event_who(self, ctx: RedContext, event_id: int):
        """List all participants of the event"""
        guild = ctx.guild
        to_list = None
        async with self.settings.guild(guild).events() as event_list:
            counter = 0
            for event in event_list:
                if event["id"] == event_id:
                    to_list = event
                    break
            
            participants = "Participants:\n\n"
            if not to_list["has_started"]:
                for uid in to_list["participants"]:
                    mbr = guild.get_member(uid)
                    participants += "{}\n".format(mbr)
                
                if len(participants) < 2000:
                    await ctx.send(participants)
                else:
                    await ctx.send_interactive(pagify(participants))

    @event.command(name="cancel")
    async def event_cancel(self, ctx: RedContext, event_id: int):
        """Cancels the specified event"""
        guild = ctx.guild
        async with self.settings.guild(guild).events() as event_list:
            to_remove = [event for event in event_list if event["id"] == event_id]
            if len(to_remove) == 0:
                await ctx.send("No event to remove!")
            else:
                event_list.remove(to_remove[0])
                await ctx.send("Removed the specified event!")
        else:
            await ctx.send("I can't remove an event that " +
                           "hasn't been created yet!")

    @commands.group()
    @checks.admin_or_permissions(manage_guild=True)
    async def eventset(self, ctx: RedContext):
        """Event maker settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @eventset.command(name="role")
    @checks.admin_or_permissions(manage_guild=True)
    async def eventset_role(self, ctx: RedContext, *, role: str=None):
        """Set the minimum role required to create events. Default 
        is for everyone to be able to create events"""
        guild = ctx.guild
        if role is not None:
            role_obj = discord.utils.get(guild.roles, name=role)
            await self.settings.guild(guild).min_role.set(role.id)
            await ctx.send("Role set to {}".format(role))
        else:
            await self.settings.guild(guild).min_role.set(0)
            await ctx.send("Role unset!")

    """
    async def check_events(self):
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
                        emb.set_footer(
                            text="Created at (UTC) " +
                            dt.utcfromtimestamp(
                                event["create_time"]).strftime(
                                    "%Y-%m-%d %H:%M:%S"))
                        emb.add_field(name="Event ID", value=str(event["id"]))
                        emb.add_field(
                            name="Participant count", value=str(
                                len(event["participants"])))
                        try:
                            await self.bot.send_message(channel, embed=emb)
                        except discord.Forbidden:
                            pass  # No permissions to send messages
                        for user in event["participants"]:
                            target = discord.utils.get(
                                self.bot.get_all_members(), id=user)
                            await self.bot.send_message(target, embed=emb)
                        event["has_started"] = True
                        save = True
            if save:
                dataIO.save_json(
                    os.path.join("data", "eventmaker", "events.json"),
                    self.events)
            await asyncio.sleep(CHECK_DELAY)
    """
