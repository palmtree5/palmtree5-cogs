import asyncio

import discord
from discord.ext import commands
from redbot.core import Config, checks
from redbot.core.context import RedContext
from redbot.core.utils.chat_formatting import warning


class Lockdown:
    """Locks down the current server"""

    default_guild = {
        "profiles": [],
        "current_lockdown_profile": {}
    }
    def __init__(self):
        self.settings = Config.get_conf(
            self, identifier=59595922, force_registration=True
        )
        self.settings.register_guild(**self.default_guild)
    
    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def lockdown(self, ctx: RedContext, profile: int=None):
        """Enables lockdown for this server"""
        guild = ctx.guild
        mod = discord.utils.get(
            guild.roles,
            id=await ctx.bot.db.guild(guild).mod_role()
        )
        admin = discord.utils.get(
            guild.roles,
            id=await ctx.bot.db.guild(guild).admin_role()
        )

        min_speaking_role = mod if mod.position < admin.position else admin
        lower_roles = sorted([r for r in guild.roles if r < min_speaking_role])
        for channel in guild.channels:
            for role in lower_roles:
                cur_role_perms = channel.overwrites_for(role)
                cur_role_perms.send_messages = False
                print("Editing channel permissions for {}".format(role.name))
                await channel.set_permissions(role, overwrite=cur_role_perms)
            bot_perms = channel.overwrites_for(guild.me)
            bot_perms_edited = False
            if not bot_perms.read_messages:
                bot_perms.read_messages = True
                bot_perms_edited = True
            if not bot_perms.send_messages:
                bot_perms.send_messages = True
                bot_perms_edited = True
            if bot_perms_edited:
                await channel.set_permissions(guild.me, overwrite=bot_perms)
        await ctx.send(
            "Server is locked down. You can unlock the server by doing {}unlockdown".format(
                ctx.prefix
            )
        )

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def unlockdown(self, ctx: RedContext):
        """Ends the lockdown for this server"""
        guild = ctx.guild
        mod = discord.utils.get(
            guild.roles,
            id=await ctx.bot.db.guild(guild).mod_role()
        )
        admin = discord.utils.get(
            guild.roles,
            id=await ctx.bot.db.guild(guild).admin_role()
        )

        min_speaking_role = mod if mod.position < admin.position else admin
        lower_roles = sorted([r for r in guild.roles if r < min_speaking_role])
        for channel in guild.channels:
            for role in lower_roles:
                cur_role_perms = channel.overwrites_for(role)
                cur_role_perms.send_messages = None
                print("Editing channel permissions for {}".format(role.name))
                await channel.set_permissions(role, overwrite=cur_role_perms)
        await ctx.send("Server has been unlocked!")
    
    @commands.group()
    @checks.admin_or_permissions(manage_guild=True)
    async def lockdownset(self, ctx: RedContext):
        """Settings for lockdown"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @lockdownset.command(name="addprofile")
    async def ld_addprofile(self, ctx: RedContext):
        """
        Interactively create a profile for lockdowns
        """
        await ctx.send("Ok, let's walk through the process of adding a profile.")
        await ctx.send(
            "What is the name of the lowest role in the hierarchy that "
            "should be allowed to speak during the lockdown?"
        )

        def msg_check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await ctx.bot.wait_for("message", check=msg_check, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send("Ok then")
            return
        
        min_role = discord.utils.get(ctx.guild.roles, name=msg.content)
        if min_role is None:
            await ctx.send("I could not find that role!")
            return
        
        lower_roles = sorted(ctx.guild.roles)[:min_role.position]

        affected_members = [m for m in ctx.guild.members if m.top_role in lower_roles]
        await ctx.send(
            "Ok, that will be the lowest role able to speak. "
            "{} members will be unable to speak during a lockdown.".format(len(affected_members))
        )

        await ctx.send("Now, let's configure the channels")

        await ctx.send("We will start with text channels")
        for channel in ctx.guild.text_channels:
            await ctx.send("Should")
            for role in lower_roles:
                if channel.overwrites_for(role).send_messages:
                    accessible_text.append(channel)
                    break
                elif channel.overwrites_for(role).send_messages is None:
                    if role.permissions.send_messages is True:
                        accessible_text.append(channel)
                        break

