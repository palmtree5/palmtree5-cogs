import discord
from redbot.core import Config, checks, commands
from redbot.core.i18n import Translator, cog_i18n

_ = Translator("MessagePinner", __file__)


@cog_i18n(_)
class MessagePinner(commands.Cog):
    """Pins messages based on configured text"""

    default_channel = {"text": ""}
    default_guild = {"cycle_pins": True}

    def __init__(self):
        self.settings = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.settings.register_channel(**self.default_channel)
        self.settings.register_guild(**self.default_guild)

    @checks.mod_or_permissions(manage_messages=True)
    @commands.command()
    @commands.guild_only()
    async def pintrigger(self, ctx: commands.Context, *, text: str = None):
        """
        Sets the pin trigger for the current channel
        If channel pins are full bot will unpin oldest pinned message
        """
        if text is None:
            channel_check = await self.settings.channel(ctx.channel).text()
            if channel_check != "":
                await self.settings.channel(ctx.channel).text.set("")
                await ctx.send(_("Cleared pin trigger!"))
            else:
                await ctx.send(_("No trigger found in this channel"))
                await ctx.send_help()
                return
        else:
            await self.settings.channel(ctx.channel).text.set(text)
            await ctx.send(_("Pin trigger text set!"))

    @commands.group(name="pinset")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def _pintrigger(self, ctx: commands.Context):
        """
        Settings for pintrigger
        """
        pass

    @_pintrigger.command(name="infinite")
    async def infinite_pins(self, ctx: commands.Context, cycle: bool = None):
        """Toggle/Set auto unpin of oldest pin when channel has reached maximum pinned messages
        """
        if cycle is None:
            load_set = await self.settings.guild(ctx.guild).cycle_pins()
            if load_set is True:
                await self.settings.guild(ctx.guild).cycle_pins.set(False)
                await ctx.send("Action Toggled: Will not unpin old pins for new pins")
                return
            else:
                await self.settings.guild(ctx.guild).cycle_pins.set(True)
                await ctx.send(
                    "Action Toggled: Whenever channel hits 49 pins I will remove the oldest pin to add a new one"
                )
                return
        else:
            load_set = await self.settings.guild(ctx.guild).cycle_pins()
            await self.settings.guild(ctx.guild).cycle_pins.set(cycle)
            if cycle:
                await ctx.send(
                    "Action Toggled: Whenever channel hits 49 pins I will remove the oldest pin to add a new one"
                )
            else:
                await ctx.send("Action Toggled: Will not unpin old pins for new pins")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Message listener"""
        if not isinstance(message.channel, discord.abc.PrivateChannel):
            this_trigger = await self.settings.channel(message.channel).text()
            if not this_trigger:
                return  # no trigger set for this channel
            pins = await message.channel.pins()
            if this_trigger in message.content and "pintrigger" not in message.content:
                cycle_pins = await self.settings.guild(message.channel.guild).cycle_pins()
                if len(pins) >= 49:
                    if cycle_pins:
                        pins.reverse()
                        remove_pin = pins[0]
                        try:
                            await remove_pin.unpin()
                            # automate unpin
                        except discord.Forbidden:
                            await message.channel.send(
                                "No permissions to do that! I "
                                "need the 'manage messages' "
                                "permission to unpin messages!"
                            )
                    else:
                        await message.channel.send(
                            "Channel pins are full. Turn on infinite pins ([p]pinset infinite`), clear the pins, or make a new channel"
                        )
                        return
                try:
                    await message.pin()  # then pin it
                except discord.Forbidden:
                    await message.channel.send(
                        "No permissions to do that! I "
                        "need the 'manage messages' "
                        "permission to pin messages!"
                    )
                except discord.NotFound:
                    print("That channel or message doesn't exist!")
                except discord.HTTPException:
                    await message.channel.send(
                        "Something went wrong. Maybe "
                        "check the number of pinned messages, and consider turning on infinite pins?"
                    )
