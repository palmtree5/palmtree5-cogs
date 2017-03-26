from discord.ext import commands
import discord
import os
from .utils import checks
from .utils.dataIO import dataIO


class MessagePinner():
    """Pins messages based on configured text"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/messagepinner/settings.json")

    @checks.mod_or_permissions(manage_messages=True)
    @commands.command(pass_context=True)
    async def pintrigger(self, ctx, *, text: str=None):
        """Sets the pin trigger for the current server"""
        server = ctx.message.server
        if text is None:
            self.settings[server.id] = None
            await self.bot.say("Cleared pin trigger!")
        else:
            self.settings[server.id] = text
            await self.bot.say("Pin trigger text set!")
        dataIO.save_json("data/messagepinner/settings.json", self.settings)

    async def on_message(self, message):
        """Message listener"""
        if not message.channel.is_private:
            if message.server.id in self.settings and self.settings[message.server.id]:
                this_trigger = self.settings[message.server.id]
                if this_trigger in message.content and "pintrigger" not in message.content:
                    try:
                        await self.bot.pin_message(message)
                    except discord.Forbidden:
                        print("No permissions to do that!")
                    except discord.NotFound:
                        print("That channel or message doesn't exist!")
                    except discord.HTTPException:
                        print("Something went wrong. Maybe check the number of pinned messages?")


def check_folder():
    """Folder check"""
    if not os.path.isdir("data/messagepinner"):
        os.mkdir("data/messagepinner")


def check_file():
    """File check"""
    if not dataIO.is_valid_json("data/messagepinner/settings.json"):
        dataIO.save_json("data/messagepinner/settings.json", {})


def setup(bot):
    """Setup function"""
    check_folder()
    check_file()
    to_add = MessagePinner(bot)
    bot.add_listener(to_add.on_message, 'on_message')
    bot.add_cog(to_add)