from redbot.core import commands, Config, checks
from redbot.core.bot import Red
import discord


class BanRole(commands.Cog):
    """
    Ban and unban by role
    """

    default_role = {"banned_members": []}

    def __init__(self, bot: Red):
        self.config = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.config.register_role(**self.default_role)
        self.bot = bot

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
                    if (mod_cog and await mod_cog.settings.guild(ctx.guild).respect_hierarchy()) or not mod_cog:
                        assert ctx.author.top_role > member.top_role or ctx.author == ctx.guild.owner
                    await ctx.guild.ban(member)
                except (discord.HTTPException, AssertionError):
                    failure_list.append("{0.name}#{0.discriminator} (id {0.id})".format(member))
                else:
                    banned_list.append(member.id)
        if failure_list:
            failures += "\n".join(failure_list)
            await ctx.send(failures)
        else:
            await ctx.tick()

    @commands.command()
    @checks.admin_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unbanrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Unban members who were banned via banrole and who had the specified role at ban time
        """
        async with self.config.role(role).banned_members() as banned_list:
            for uid in banned_list:
                try:
                    await ctx.guild.unban(discord.Object(id=uid))
                except discord.Forbidden:
                    return await ctx.send("I am unable to do that for some reason.")
                except discord.NotFound:
                    banned_list.remove(uid)
                else:
                    banned_list.remove(uid)
        await ctx.tick()
