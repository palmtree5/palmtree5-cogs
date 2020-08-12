import sys
import discord
import asyncio
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box

from itertools import zip_longest


class Lockdown(commands.Cog):
    """
    Locks down the current server

    To get started, you will need to set up a role to be used when locking
    down your server. This role needs to be above all roles it should affect
    in the hierarchy as it will be used to determine who should be affected
    by the lockdown and this role will be applied to each user. The 
    role's permissions should be set up to deny access to things the affected 
    users should not be able to do during a lockdown (such as sending messages, 
    talking in voice channels, adding reactions, etc).

    Once you've set up the role, you can create a new profile with
    `[p]lockdownset addprofile` (which takes the role (ID, mention, or name)
    as an argument).

    Please note that `[p]lockdown` will not work if no profiles are
    available as this cog depends on using roles to run a lockdown.
    """

    default_guild = {"profiles": {}, "next_profile_id": 1, "current_lockdown_role_id": 0}
    default_member = {"old_permissions": {}}

    def __init__(self):
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_guild(**self.default_guild)
        self.settings.register_member(**self.default_member)

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def lockdown(self, ctx: commands.Context, profile: str):
        """Enables lockdown for this server

        A profile ID must be specified. To list profiles,
        do `[p]lockdownset listprofiles`"""
        guild = ctx.guild

        profiles = await self.settings.guild(ctx.guild).get_raw("profiles")

        if profile not in profiles:
            await ctx.send("That profile does not exist!")
            return
        role = discord.utils.get(guild.roles, id=profiles[profile])
        targets = [m for m in guild.members if m.top_role <= role]

        if not guild.me.guild_permissions.manage_roles:
            return await ctx.send("I can't manage roles in this server!")

        for target in targets:
            await target.add_roles(role, reason=f"Server lockdown requested by {ctx.author}.")
            await asyncio.sleep(1)
        await self.settings.guild(ctx.guild).current_lockdown_role_id.set(role.id)
        await ctx.send(
            "Server is locked down. You can unlock the server by doing "
            "{}unlockdown".format(ctx.prefix)
        )

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def unlockdown(self, ctx: commands.Context):
        """Ends the lockdown for this server"""
        guild = ctx.guild

        role_id = await self.settings.guild(guild).current_lockdown_role_id()
        role = discord.utils.get(guild.roles, id=role_id)
        targets = [m for m in guild.members if m.top_role == role]
        
        if not guild.me.guild_permissions.manage_roles:
            return await ctx.send("I can't manage roles in this server!")

        for target in targets:
            await target.remove_roles(role, reason=f"Lockdown end requested by {ctx.author}.")
            await asyncio.sleep(1)
        await self.settings.guild(guild).current_lockdown_role_id.set(0)
        await ctx.send("Server has been unlocked!")

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def lockdownset(self, ctx: commands.Context):
        """Settings for lockdown"""
        pass

    @lockdownset.command(name="reset")
    @checks.guildowner_or_permissions(administrator=True)
    async def ld_reset(self, ctx: commands.Context):
        """
        Removes all lockdown profiles for the current guild.
        """
        await self.settings.guild(ctx.guild).profiles.set({})
        await self.settings.guild(ctx.guild).next_profile_id.set(1)
        await ctx.tick()

    @lockdownset.command(name="listprofiles")
    async def ld_listprofiles(self, ctx: commands.Context):
        """
        List all lockdown profiles for the guild.
        """
        profiles = await self.settings.guild(ctx.guild).get_raw("profiles")
        output = "{:<4}{}\n".format("ID", "Role Name")
        rs = []
        for lockdown_id, role_id in profiles.items():
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            rs.append("{:<4}{}".format("{}.".format(lockdown_id), role))
        if rs:
            output += "\n".join(sorted(rs))
        else:
            output = "There are no profiles set up!"
        await ctx.send(box(output))

    @lockdownset.command(name="addprofile")
    @checks.admin_or_permissions(manage_guild=True)
    async def ld_addprofile(self, ctx: commands.Context, role: discord.Role):
        """
        Adds a lockdown profile.

        Role is the role to be applied when triggering a lockdown
        with this profile.
        """
        next_id = await self.settings.guild(ctx.guild).next_profile_id()
        await self.settings.guild(ctx.guild).profiles.set_raw(next_id, value=role.id)
        await self.settings.guild(ctx.guild).next_profile_id.set(next_id + 1)
        await ctx.send("Profile {} added for role {}".format(next_id, role))

    @lockdownset.command(name="removeprofile")
    @checks.admin_or_permissions(manage_guild=True)
    async def ld_removeprofile(self, ctx: commands.Context, profile_id: int):
        """
        Removes the lockdown profile with the specified IDs

        To see a list of profiles and their IDs,
        do `[p]lockdownset listprofiles`
        """
        profiles = await self.settings.guild(ctx.guild).get_raw("profiles")
        if profile_id in profiles:
            del profiles[profile_id]
            await self.settings.guild(ctx.guild).set_raw("profiles", value=profiles)
            await ctx.tick()
        else:
            await ctx.send("That profile doesn't exist!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Handle applying lockdown role to new joins
        """
        role_id = await self.settings.guild(member.guild).current_lockdown_role_id()
        if role_id == 0:  # No lockdown in progress, so nothing to do here
            return
        role = discord.utils.get(member.guild.roles, id=role_id)
        await member.add_roles(role)
