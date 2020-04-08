import asyncio
import contextlib
from datetime import datetime as dt, timezone

import discord
from redbot.core import commands
from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify, warning
from redbot.core.i18n import Translator

from .helpers import (
    parse_time,
    allowed_to_create,
    get_event_embed,
    allowed_to_edit,
    check_event_start,
)
from .menus import event_menu

_ = Translator("EventMaker", __file__)


class EventMaker(commands.Cog):
    """
    A tool for creating events inside of Discord. Anyone can
    create an event by default. If a specific role has been
    specified, users must have that role or any role above it in
    the hierarchy or be the server owner to create events.
    """

    default_guild = {"events": [], "min_role": 0, "next_available_id": 1, "channel": 0}

    default_member = {"dms": False}

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_guild(**self.default_guild)
        self.settings.register_member(**self.default_member)
        loop = self.bot.loop
        self.event_check_task = loop.create_task(self.check_events())

    def cog_unload(self):
        self.event_check_task.cancel()

    @commands.group()
    @commands.guild_only()
    async def event(self, ctx: commands.Context):
        """Base command for events"""
        pass

    @event.command(name="create")
    @allowed_to_create()
    async def event_create(self, ctx: commands.Context):
        """
        Wizard-style event creation tool.

        The event will only be created if all information is provided properly.
        If a minimum required role has been set, users must have that role or
        higher, be in the mod/admin role, or be the guild owner in order to use this command
        """
        author = ctx.author
        guild = ctx.guild

        event_id = await self.settings.guild(guild).next_available_id()

        creation_time = ctx.message.created_at
        if creation_time.tzinfo is None:
            creation_time = creation_time.replace(tzinfo=timezone.utc).timestamp()
        else:
            creation_time = creation_time.timestamp()
        await ctx.send(_("Enter a name for the event: "))

        def same_author_check(msg):
            return msg.author == author

        msg = await self.bot.wait_for("message", check=same_author_check)
        name = msg.content
        if len(name) > 256:
            await ctx.send(
                _("That name is too long! Event names must be 256 charcters or less.")
            )
            return
        await ctx.send(
            "Enter the amount of time from now the event will take "
            "place (valid units are w, d, h, m, s): "
        )
        msg = await self.bot.wait_for("message", check=same_author_check)
        start_time = parse_time(creation_time, msg)
        if start_time is None:
            await ctx.send("Something went wrong with parsing the time you entered!")
            return
        await ctx.send("Enter a description for the event: ")
        msg = await self.bot.wait_for("message", check=same_author_check, timeout=60)
        if len(msg.content) > 1000:
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
            "participants": [author.id],
        }
        async with self.settings.guild(guild).events() as event_list:
            event_list.append(new_event)
            event_list.sort(key=lambda x: x["create_time"])
        await self.settings.guild(guild).next_available_id.set(event_id + 1)
        await ctx.send(embed=get_event_embed(guild, ctx.message.created_at, new_event))

    @event.command(name="join")
    async def event_join(self, ctx: commands.Context, event_id: int):
        """Join an event"""
        guild = ctx.guild
        to_join = None
        async with self.settings.guild(guild).events() as event_list:
            for event in event_list:
                if event["id"] == event_id:
                    to_join = event
                    event_list.remove(event)
                    break

            if not to_join:
                return await ctx.send("I could not find an event with that id!")

            if not to_join["has_started"]:
                if ctx.author.id not in to_join["participants"]:
                    to_join["participants"].append(ctx.author.id)
                    await ctx.tick()
                    event_list.append(to_join)
                    event_list.sort(key=lambda x: x["id"])
                else:
                    await ctx.send("You have already joined that event!")
            else:
                await ctx.send("That event has already started!")

    @event.command(name="leave")
    async def event_leave(self, ctx: commands.Context, event_id: int):
        """Leave the specified event"""
        guild = ctx.guild
        to_leave = None
        async with self.settings.guild(guild).events() as event_list:
            for event in event_list:
                if event["id"] == event_id:
                    to_leave = event
                    event_list.remove(event)
                    break

            if not to_leave:
                return await ctx.send("I could not find an event with that id!")

            if not to_leave["has_started"]:
                if ctx.author.id in to_leave["participants"]:
                    to_leave["participants"].remove(ctx.author.id)
                    await ctx.send("Left the event!")
                    event_list.append(to_leave)
                    event_list.sort(key=lambda x: x["id"])
                else:
                    await ctx.send("You are not part of that event!")

    @event.command(name="list")
    async def event_list(self, ctx: commands.Context, started: bool = False):
        """List events for this server that have not started yet

        If `started` is True, include events that have already started"""
        guild = ctx.guild
        events = []
        async with self.settings.guild(guild).events() as event_list:
            for event in event_list:
                if started:
                    emb = get_event_embed(guild, ctx.message.created_at, event)
                    events.append(emb)
                else:
                    if not event["has_started"]:
                        emb = get_event_embed(guild, ctx.message.created_at, event)
                        events.append(emb)
        if len(events) == 0:
            await ctx.send("No events available to join!")
        else:
            await event_menu(ctx, events, message=None, page=0, timeout=30)

    @event.command(name="who")
    async def event_who(self, ctx: commands.Context, event_id: int):
        """List all participants for the event"""
        guild = ctx.guild
        to_list = None
        async with self.settings.guild(guild).events() as event_list:
            for event in event_list:
                if event["id"] == event_id:
                    to_list = event
                    break
            else:
                await ctx.send(_("I could not find an event with that id!"))
                return

            participants = "Participants:\n\n"
            mbr_list = [
                "{}".format(guild.get_member(uid))
                for uid in to_list["participants"]
                if guild.get_member(uid)
            ]
            participants += "\n".join(mbr_list)
            if len(participants) < 2000:
                await ctx.send(participants)
            else:
                await ctx.send_interactive(pagify(participants))

    @event.command(name="cancel")
    async def event_cancel(self, ctx: commands.Context, event_id: int):
        """Cancels the specified event"""
        guild = ctx.guild
        async with self.settings.guild(guild).events() as event_list:
            to_remove = [event for event in event_list if event["id"] == event_id]
            if len(to_remove) == 0:
                await ctx.send("No event to remove!")
            else:
                event = to_remove[0]
                if not await allowed_to_edit(ctx, event):
                    await ctx.send("You are not allowed to edit that event!")
                    return
                event_list.remove(to_remove[0])
                await ctx.tick()

    @commands.group()
    @commands.guild_only()
    async def eventset(self, ctx: commands.Context):
        """Event maker settings"""
        pass

    @eventset.command(name="toggledms")
    @commands.guild_only()
    async def eventset_toggledms(self, ctx: commands.Context, user: discord.Member = None):
        """
        Toggles event start announcement DMs for the specified user

        By default, users will not receive event start announcements via DM

        If `user` is not specified, toggle for the author.

        Only admins and the guild owner may toggle DMs for users other than themselves
        """
        if user:
            if not await ctx.bot.is_admin(ctx.author) and not ctx.author == ctx.guild.owner:
                await ctx.send("You are not allowed to toggle that for other users!")
                return
        if not user:
            user = ctx.author
        cur_val = await self.settings.member(user).dms()
        await self.settings.member(user).dms.set(False if cur_val else True)
        await ctx.tick()

    @eventset.command(name="role")
    @checks.admin_or_permissions(manage_guild=True)
    async def eventset_role(self, ctx: commands.Context, *, role: discord.Role = None):
        """Set the minimum role required to create events.

        Default is for everyone to be able to create events"""
        guild = ctx.guild
        if role is not None:
            await self.settings.guild(guild).min_role.set(role.id)
            await ctx.send("Role set to {}".format(role))
        else:
            await self.settings.guild(guild).min_role.set(0)
            await ctx.send("Role unset!")

    @eventset.command(name="resetevents")
    @checks.guildowner_or_permissions(administrator=True)
    async def eventset_resetevents(self, ctx: commands.Context, confirm: str = None):
        """
        Resets the events list for this guild
        """
        if confirm is None or confirm.lower() != "yes":
            await ctx.send(
                warning(
                    "This will remove all events for this guild! "
                    "This cannot be undone! To confirm, type "
                    "`{}eventset resetevents yes`".format(ctx.prefix)
                )
            )
        else:
            await self.settings.guild(ctx.guild).events.set([])
            await self.settings.guild(ctx.guild).next_available_id.set(1)
            await ctx.tick()

    @eventset.command(name="channel")
    @checks.admin_or_permissions(manage_guild=True)
    async def eventset_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Sets the channel where event start announcements will be sent

        If this is not set, the channel will default to the channel used
        for new member messages (Server Settings > Overview > New Member
        Messages Channel on desktop). If that is set to `No new member messages`,
        the event start announcement will not be sent to a channel in the server
        and will only be sent directly to the participants via DM
        """
        await self.settings.guild(ctx.guild).channel.set(channel.id)
        await ctx.tick()

    async def check_events(self):
        CHECK_DELAY = 300
        while self == self.bot.get_cog("EventMaker"):
            for guild in self.bot.guilds:
                async with self.settings.guild(guild).events() as event_list:
                    channel = guild.get_channel(await self.settings.guild(guild).channel())
                    if channel is None:
                        channel = guild.system_channel
                    for event in event_list:
                        changed, data = await check_event_start(channel, event, self.settings)
                        if not changed:
                            continue
                        event_list.remove(event)
                        event_list.append(data)
                    event_list.sort(key=lambda x: x["create_time"])
            await asyncio.sleep(CHECK_DELAY)
