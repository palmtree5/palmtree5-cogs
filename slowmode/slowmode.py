import contextlib

import discord
from discord.ext import commands
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold


class SlowMode:
    """A slowmode cog for Red V3"""

    default_channel = {
        "time": 0
    }

    default_guild = {
        "min_exempt_role": 0
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(
            self, identifier=59595922, force_registration=True
        )
        self.settings.register_channel(**self.default_channel)
        self.settings.register_guild(**self.default_guild)
        self.msg_sender_cache = {}

    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.command()
    async def toggleslow(self, ctx: commands.Context, time: int=0):
        """
        Slow the chat

        `time` is the time in seconds users must wait after sending a message
        to be able to send another message.

        If a role has been set with `[p]slowset role`, users with a top role
        below that role in the hierarchy will be affected by slow mode.
        Otherwise, all users except those with the mod role or admin role
        will be affected by slow mode. The guild owner is always exempt from
        slow mode.
        """
        if time < 0:
            await ctx.send("Invalid time specified! Time must be 0 or greater")
            return

        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(
                "I cannot manage messages in this channel! Slow mode "
                "has not been activated as a result!"
            )
            return
        await self.settings.channel(ctx.channel).time.set(time)
        if time > 0:
            await ctx.send(
                bold(
                    "{0.mention} is now in slow mode. You may send 1 message "
                    "every {1} seconds".format(ctx.channel, time)
                )
            )
        else:
            await ctx.send(
                bold(
                    "Slow mode has been disabled for {0.mention}".format(
                        ctx.channel
                    )
                )
            )

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def slowset(self, ctx: commands.Context):
        """
        Slow mode settings
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @slowset.command(name="role")
    async def slowset_role(self, ctx: commands.Context, role: discord.Role):
        """
        Sets the minimum role to be exempt from slow mode

        Any role at or above the specified role will be exempt from slow
        mode, so any roles that should be affected by slow mode should be
        below this role in the hierarchy
        """
        await self.settings.guild(ctx.guild).min_exempt_role.set(role.id)
        await ctx.tick()

    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        channel_slow = await self.settings.channel(message.channel).time()
        if channel_slow == 0:
            return
        minimum_role_id = await self.settings.guild(message.guild).min_exempt_role()
        if minimum_role_id == 0:
            if await self.bot.is_mod(message.author) or \
                    message.author == message.guild.owner:
                return
        role = discord.utils.get(message.guild.roles, id=minimum_role_id)
        if message.author.top_role >= role or message.author == message.guild.owner:
            return
        if message.author.id not in self.msg_sender_cache:
            next_talk_time = message.created_at.timestamp() + channel_slow
            self.msg_sender_cache[message.author.id] = next_talk_time
        else:
            if message.created_at.timestamp() < self.msg_sender_cache[str(message.author.id)]:
                with contextlib.suppress(discord.Forbidden):
                    await message.delete()
