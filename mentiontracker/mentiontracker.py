from discord.ext import commands
import discord
import os
from .utils.dataIO import dataIO


class MentionTracker():
    """Notifies people of mentions in servers they enable it for"""
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/mentiontracker/settings.json")

    @commands.command(pass_context=True)
    async def trackmentions(self, ctx, status: str, channel: discord.Channel=None):
        """Toggles mention tracking for the specified channel.
           Defaults to the current channel."""
        if not channel:
            channel = ctx.message.channel
        author = ctx.message.author
        if author.id not in self.settings:
            self.settings[author.id] = {}
        if channel.id not in self.settings[author.id]:
            self.settings[author.id][channel.id] = None
        if status.lower() == "on" or status.lower() == "off":
            self.settings[author.id][channel.id] = True if status.lower() == "on" else False
            dataIO.save_json("data/mentiontracker/settings.json", self.settings)
            await self.bot.say("Mention tracker toggled!")
        else:
            await self.bot.say("Invalid status specified!")

    async def check_message(self, message):
        if len(message.mentions) > 0:
            for mention in message.mentions:
                if mention.id in self.settings and message.channel.id in\
                        self.settings[mention.id] and\
                        self.settings[mention.id][message.channel.id]:
                    emb = discord.Embed(title="You were mentioned!", description=message.content)
                    emb.add_field(name="Mentioner", value=message.author.name + "#" + message.author.discriminator, inline=False)
                    emb.add_field(name="Server", value=message.server.name, inline=False)
                    emb.add_field(name="Channel", value=message.channel.name, inline=False)
                    emb.set_footer(text=str(message.timestamp) + " UTC")
                    user = discord.utils.get(self.bot.get_all_members(), id=mention.id)
                    await self.bot.send_message(user, embed=emb)


def check_folder():
    if not os.path.isdir("data/mentiontracker"):
        os.mkdir("data/mentiontracker")


def check_file():
    if not dataIO.is_valid_json("data/mentiontracker/settings.json"):
        dataIO.save_json("data/mentiontracker/settings.json", {})


def setup(bot):
    check_folder()
    check_file()
    n = MentionTracker(bot)
    bot.add_listener(n.check_message, "on_message")
    bot.add_cog(n)
