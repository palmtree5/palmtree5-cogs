from redbot.core import commands
import discord

from redbot.core import Config, checks, commands
from redbot.core.i18n import Translator, cog_i18n

_ = Translator("MessagePinner", __file__)


@cog_i18n(_)
class MessagePinner(commands.Cog):
    """Pins messages based on configured text"""

    default_channel = {"text": ""}

    def __init__(self):
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_channel(**self.default_channel)

    @checks.mod_or_permissions(manage_messages=True)
    @commands.command()
    @commands.guild_only()
    async def pintrigger(self, ctx: commands.Context, *, text: str = None):
        """Sets the pin trigger for the current channel"""
        if text is None:
            await self.settings.channel(ctx.channel).text.set("")
            await ctx.send(_("Cleared pin trigger!"))
        else:
            await self.settings.channel(ctx.channel).text.set(text)
            await ctx.send(_("Pin trigger text set!"))

    async def on_message(self, message):
        """Message listener"""
        if not isinstance(message.channel, discord.abc.PrivateChannel):
            this_trigger = await self.settings.channel(message.channel).text()
            if not this_trigger:
                return  # no trigger set for this channel
            if this_trigger in message.content and "pintrigger" not in message.content:
                try:
                    await message.pin()
                except discord.Forbidden:
                    await message.channel.send(
                        "No permissions to do that! I "
                        "need the 'manage messages' "
                        "permission to do pin messages!"
                    )
                except discord.NotFound:
                    print("That channel or message doesn't exist!")
                except discord.HTTPException:
                    await message.channel.send(
                        "Something went wrong. Maybe " "check the number of pinned messages?"
                    )
