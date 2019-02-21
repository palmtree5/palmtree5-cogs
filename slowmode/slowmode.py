from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold
import discord


class SlowMode(commands.Cog):
    """A slowmode cog for Red V3"""

    def __init__(self, bot: Red):
        self.bot = bot

    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.command()
    async def toggleslow(self, ctx: commands.Context, time: int = 0):
        """
        Slow the chat

        `time` is the time in seconds users must wait after sending a message
        to be able to send another message.
        """
        if time < 0 or time > 120:
            embed = discord.Embed(title="Error!", description="Invalid time specified! Time must be between 0 and 120 (inclusive)", color=0xf44146)
            await ctx.send(embed=embed)
            return
        try:
            await ctx.channel.edit(slowmode_delay=time)
        except discord.Forbidden:
            embed = discord.Embed(title="Error!", description="I am forbidden from doing that...Sorry!", color=0xf44146)
            await ctx.send(embed=embed)
            return
        if time > 0:
            embed = discord.Embed(title="Slow Mode Activated", description="{0.mention} is now in slow mode. You may send 1 message every {1} seconds)".format(ctx.channel, time), color=0x41f4e8)
            embed.set_thumbnail(url="https://i.imgur.com/zegCAq4.png")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Slow Mode Disabled", description="Slow mode has been disabled for {0.mention}".format(ctx.channel), color=0xaaf442)
            embed.set_thumbnail(url="https://i.imgur.com/zegCAq4.png")
            await ctx.send(embed=embed)
