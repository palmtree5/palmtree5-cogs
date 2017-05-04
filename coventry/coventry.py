import discord
import asyncio
from discord.ext import commands
from core import checks
from __main__ import settings


class Coventry():
    """A cog for giving users their own little space to yell where
       nobody else can hear what they're saying"""
    def __init__(self, bot):
        self.bot = bot

    @commands.group(no_pm=True, pass_context=True, name="coventry")
    @checks.admin_or_permissions(manage_guild=True)
    async def _coventry(self, ctx):
        """Commands for giving users their own private yelling space where
           nobody but mods or admins can see their messages"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_coventry.command(no_pm=True, pass_context=True, name="send")
    @checks.admin_or_permissions(manage_guild=True)
    async def _send(self, ctx, user: discord.Member):
        """Send a user to Coventry"""
        guild = ctx.message.guild
        for usr in ctx.message.mentions:
            if usr != ctx.message.author:
                is_mod_or_admin = False
                for r in usr.roles:
                    if r.name == settings.get_server_mod(guild):
                        is_mod_or_admin = True
                    elif r.name == settings.get_server_admin(guild):
                        is_mod_or_admin = True
                if not is_mod_or_admin:
                    chrolename = usr.name + usr.discriminator
                    covrole = await self.bot.create_role(
                        guild,
                        name=chrolename
                    )
                    await self.bot.add_roles(usr, covrole)
                    admin_role = discord.utils.get(
                        guild.roles,
                        name=settings.get_server_admin(guild)
                    )
                    mod_role = discord.utils.get(
                        guild.roles,
                        name=settings.get_server_mod(guild)
                    )
                    everyone_perms = discord.PermissionOverwrite(
                        read_messages=False
                    )
                    insilenced_perms = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True
                    )
                    mod_admin_perms = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_channel=True
                    )
                    if not mod_role and not admin_role:
                        chn = await self.bot.create_channel(
                            guild,
                            chrolename,
                            (guild.default_role, everyone_perms),
                            (covrole, insilenced_perms)
                        )
                    elif not mod_role:
                        chn = await self.bot.create_channel(
                            guild,
                            chrolename,
                            (guild.default_role, everyone_perms),
                            (covrole, insilenced_perms),
                            (admin_role, mod_admin_perms)
                        )
                    elif not admin_role:
                        chn = await self.bot.create_channel(
                            guild,
                            chrolename,
                            (guild.default_role, everyone_perms),
                            (covrole, insilenced_perms),
                            (mod_role, mod_admin_perms)
                        )
                    else:
                        chn = await self.bot.create_channel(
                            guild,
                            chrolename,
                            (guild.default_role, everyone_perms),
                            (covrole, insilenced_perms),
                            (mod_role, mod_admin_perms),
                            (admin_role, mod_admin_perms)
                        )
                    await asyncio.sleep(1)
                    for c in guild.channels:
                        if c.name != chn.name:
                            try:
                                await self.bot.edit_channel_permissions(
                                    c,
                                    covrole,
                                    everyone_perms
                                )
                            except discord.errors.Forbidden:
                                pass
            await ctx.send("Done")

    @_coventry.command(no_pm=True, pass_context=True, name="retrieve")
    @checks.admin_or_permissions(manage_guild=True)
    async def _retrieve(self, ctx, user: discord.Member):
        """Retrieve a user from Coventry"""
        guild = ctx.message.guild
        if user is None:
            await self.bot.say("Hey, you didn't specify a user!")
        else:
            for usr in ctx.message.mentions:
                has_cov_role = False
                cur_cov_role = usr.name + usr.discriminator
                cov_role = None
                for r in usr.roles:
                    if r.name == cur_cov_role:
                        has_cov_role = True
                        cov_role = r
                if has_cov_role:
                    await self.bot.delete_role(guild, cov_role)
                    chn = None
                    for c in list(guild.channels):
                        if c.name == cur_cov_role:
                            chn = c
                    await self.bot.delete_channel(chn)
            await self.bot.say("Done")

