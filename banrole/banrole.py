from io import BytesIO
import logging
from typing import Dict, Literal
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
import discord

log = logging.getLogger("red.palmtree5cogs.banrole")

RequesterTypes = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class BanRole(commands.Cog):
    """
    Ban and unban by role
    """

    default_role = {"banned_members": []}

    def __init__(self, bot: Red):
        self.config = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.config.register_role(**self.default_role)
        self.bot = bot

    async def red_get_data_for_user(self, *, user_id: int) -> Dict[str, BytesIO]:
        all_role_data = await self.config.all_roles()
        role_ids_with_user = []
        for k, v in all_role_data.items():
            if user_id in v["banned_members"]:
                role_ids_with_user.append(k)
        if not role_ids_with_user:
            return {}
        content = f"Server role bans for Discord user with id {user_id}:\n"
        for rid in role_ids_with_user:
                for guild in self.bot.guilds:
                    role = guild.get_role(rid)
                    if role:
                        content += f"{role.name} ({role.id} in server {guild.name} ({guild.id})\n"
                        break
        return {
            "user_data.txt": BytesIO(content.encode())
        }
    
    async def red_delete_data_for_user(self, *, requester: RequesterTypes, user_id: int) -> None:
        if requester == "discord_deleted_user" or requester == "owner":
            # User doesn't exist anymore or the bot owner is removing 
            # the data of their own accord not for a user request
            all_role_data = await self.config.all_roles()
            to_process = {}
            for k, v in all_role_data.items():
                ban_list = v["banned_members"]
                if user_id in ban_list:
                    to_process[k] = v
            if to_process:
                for k, v in to_process:
                    for guild in self.bot.guilds:
                        role = guild.get_role(k)
                        if role:
                            bans = v["banned_members"]
                            bans.remove(user_id)
                            await self.config.role(role).set_raw("banned_members", value=bans)
                            break
            else:
                return
        else:
            log.info("Requester type is user, user_strict, or unknown: not removing user id due to operational needs")
            return

    @commands.command()
    @checks.admin_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def banrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Ban all members with the specified role

        The bot's role must be higher than the role you want to ban
        """
        failures = "I failed to ban the following members:\n"
        failure_list = []
        mod_cog = self.bot.get_cog("Mod")
        async with self.config.role(role).banned_members() as banned_list:
            for member in role.members:
                try:
                    assert ctx.guild.me.top_role > member.top_role and ctx.guild.owner != member
                    if (mod_cog and await mod_cog.config.guild(ctx.guild).respect_hierarchy()) or not mod_cog:
                        assert ctx.author.top_role > member.top_role or ctx.author == ctx.guild.owner
                    await ctx.guild.ban(member)
                except (discord.HTTPException, AssertionError):
                    failure_list.append("{0.name}#{0.discriminator} (id {0.id})".format(member))
                else:
                    banned_list.append(member.id)
        if failure_list:
            failures += "\n".join(failure_list)
            for page in pagify(failures):
                await ctx.send(page)
        else:
            await ctx.tick()

    @commands.command()
    @checks.admin_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unbanrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Unban members who were banned via banrole and who had the specified role at ban time
        """
        failures = "I failed to unban the following users:\n"
        failure_list = []
        async with self.config.role(role).banned_members() as banned_list:
            for uid in banned_list:
                try:
                    await ctx.guild.unban(discord.Object(id=uid))
                except discord.Forbidden:
                    failure_list.append(uid)
                    banned_list.remove(uid)
                except discord.NotFound:
                    failure_list.append(uid)
                    banned_list.remove(uid)
                else:
                    banned_list.remove(uid)
        if failure_list:
            failures += "\n".join(failure_list)
            for page in pagify(failures):
                await ctx.send(page)
        await ctx.tick()
