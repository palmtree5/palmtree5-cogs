from discord.ext import commands
import discord
from redbot.core import checks


class Lockdown:
    """Locks down the current server"""

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def lockdown(self, ctx: commands.Context):
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
    async def unlockdown(self, ctx: commands.Context):
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
