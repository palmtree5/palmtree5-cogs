import discord
import asyncio
from discord.ext import commands
from core import checks, Config
from core.bot import Red


class Coventry:
    """A cog for giving users their own little space to yell where
       nobody else can hear what they're saying"""

    default_member = {
        "in_coventry": False,
        "covrole": None,
        "covchannel": None
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 59595922, force_registration=True)
        self.config.register_member(**self.default_member)

    async def check_exempt(self, user: discord.Member, guild: discord.Guild):
        mod_role_id = await self.bot.db.guild(guild).mod_role()
        admin_role_id = await self.bot.db.guild(guild).admin_role()

        if await self.bot.is_owner(user) or user == guild.owner:
            return True
        elif [r for r in guild.roles if r.id == admin_role_id][0] in user.roles:
            return True
        elif [r for r in guild.roles if r.id == mod_role_id][0] in user.roles:
            return True
        else:
            return False

    @commands.group(name="coventry")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def _coventry(self, ctx):
        """Commands for giving users their own private yelling space where
           nobody but mods or admins can see their messages"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_coventry.command(name="send")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def _send(self, ctx):
        """Send a user to Coventry
        This command has no args but
        will fail if no users are mentioned"""
        guild = ctx.guild
        if len(ctx.message.mentions) == 0:
            await ctx.send("No users mentioned!")
            return
        for usr in ctx.message.mentions:
            if usr != ctx.author:
                if not await self.check_exempt(usr, guild):
                    chrolename = usr.name + usr.discriminator
                    covrole = await guild.create_role(
                        name=chrolename
                    )
                    await usr.add_roles(covrole)
                    admin_role = discord.utils.get(
                        guild.roles,
                        id=await self.bot.db.guild(guild).admin_role()
                    )
                    mod_role = discord.utils.get(
                        guild.roles,
                        id=await self.bot.db.guild(guild).mod_role()
                    )
                    everyone_perms = discord.PermissionOverwrite(
                        read_messages=False,
                        send_messages=False
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
                        overwrites = {
                            guild.default_role: everyone_perms,
                            covrole: insilenced_perms
                        }
                        chn = await guild.create_text_channel(
                            chrolename,
                            overwrites=overwrites
                        )
                    elif not mod_role:
                        overwrites = {
                            guild.default_role: everyone_perms,
                            covrole: insilenced_perms,
                            admin_role: mod_admin_perms
                        }
                        chn = await guild.create_text_channel(
                            chrolename,
                            overwrites=overwrites
                        )
                    elif not admin_role:
                        overwrites = {
                            guild.default_role: everyone_perms,
                            covrole: insilenced_perms,
                            mod_role: mod_admin_perms
                        }
                        chn = await guild.create_text_channel(
                            chrolename,
                            overwrites=overwrites
                        )
                    else:
                        overwrites = {
                            guild.default_role: everyone_perms,
                            covrole: insilenced_perms,
                            admin_role: mod_admin_perms,
                            mod_role: mod_admin_perms
                        }
                        chn = await guild.create_text_channel(
                            chrolename,
                            overwrites=overwrites
                        )
                    await asyncio.sleep(1)
                    for c in guild.channels:
                        usr_perms = c.permissions_for(usr)
                        can_read_or_send = usr_perms.send_messages or usr_perms.read_messages
                        if c.name != chn.name and can_read_or_send:
                            try:
                                await c.set_permissions(
                                    covrole,
                                    overwrite=everyone_perms
                                )
                            except discord.errors.Forbidden:
                                pass
                    await self.config.member(usr).in_coventry.set(True)
                    await self.config.member(usr).covrole.set(covrole.id)
                    await self.config.member(usr).covchannel.set(chn.id)
            await ctx.send("Done")

    @_coventry.command(name="retrieve")
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def _retrieve(self, ctx):
        """Retrieve a user from Coventry
        This command has no args but
        will fail if no users are mentioned"""
        guild = ctx.guild
        if len(ctx.message.mentions) == 0:
            await ctx.send("No users mentioned!")
        else:
            for usr in ctx.message.mentions:
                in_coventry = await self.config.member(usr).in_coventry()
                if not in_coventry:
                    await ctx.send(
                        "Skipping user {}#{} because they are "
                        "not in coventry".format(usr.name, usr.discriminator)
                    )
                    continue
                covrole = discord.utils.get(
                    guild.roles,
                    id=await self.config.member(usr).covrole()
                )
                
                await covrole.delete()
                chn = guild.get_channel(await self.config.member(usr).covchannel())
                await chn.delete()
                await self.config.member(usr).clear()
                asyncio.sleep(1)
            await ctx.send("Done.")

