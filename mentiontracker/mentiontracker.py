from discord.ext import commands
import discord
import os
import logging
from .utils.dataIO import dataIO
from .utils.chat_formatting import box


log = logging.getLogger("red.mentiontracker")


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

    @commands.command(pass_context=True)
    async def trackword(self, ctx: commands.Context, word: str, channel: discord.Channel=None):
        """Toggle tracking of the specified word in the specified channel
        Required parameters:
        - word: the word to add or remove
          - if the word is in the list, it will be removed
          - if it is not in the list, it will be added
        Optional parameters:
        - channel: the channel to track the word for (defaults to the current channel if not specified)"""
        author = ctx.message.author
        if not channel:
            channel = ctx.message.channel
        if author.id not in self.settings:
            self.settings[author.id] = {}
        if "words" not in self.settings[author.id]:
            self.settings[author.id]["words"] = {}
        if channel.id not in self.settings[author.id]["words"]:
            self.settings[author.id]["words"][channel.id] = []
        added = False
        cur_list = self.settings[author.id]["words"][channel.id]
        if word not in cur_list:
            cur_list.append(word)
            added = True
        else:
            cur_list.remove(word)
        self.settings[author.id]["words"][channel.id] = cur_list
        dataIO.save_json("data/mentiontracker/settings.json", self.settings)
        if added:
            await self.bot.say("Added '{}' to the tracking list for {}".format(word, channel.mention))
        else:
            await self.bot.say("Removed '{}' from the trackling list for {}".format(word, channel.mention))

    @commands.command(pass_context=True)
    async def listwords(self, ctx: commands.Context, channel: discord.Channel=None):
        """List all words for the specified channel
        Optional parameters:
        - channel: the channel to show words for (defaults to the current channel)"""
        author = ctx.message.author
        if not channel:
            channel = ctx.message.channel
        if author.id not in self.settings or\
                "words" not in self.settings[author.id] or\
                channel.id not in self.settings[author.id]["words"] or\
                not self.settings[author.id]["words"][channel.id]:
            await self.bot.say("You haven't set any words to be tracked!")
        else:
            head = "Tracked words for {}#{} in #{}".format(author.name, author.discriminator, channel.name)
            msg = ""
            for word in self.settings[author.id]["words"][channel.id]:
                msg += "{}\n".format(word)
            await self.bot.say(box(msg, lang=head))

    async def check_message(self, message):
        """Check function for checking user mention settings
        and the user's word list for the message's channel"""
        if len(message.mentions) > 0:
            for mention in message.mentions:
                if mention.id in self.settings and message.channel.id in\
                        self.settings[mention.id] and\
                        self.settings[mention.id][message.channel.id]:
                    emb = discord.Embed(
                        title="You were mentioned!",
                        description=message.content
                    )
                    emb.add_field(
                        name="Mentioner",
                        value="{}#{}".format(
                            message.author.name,
                            message.author.discriminator
                        ),
                        inline=False
                    )
                    emb.add_field(
                        name="Server",
                        value=message.server.name,
                        inline=False
                    )
                    emb.add_field(
                        name="Channel",
                        value=message.channel.name,
                        inline=False
                    )
                    emb.set_footer(text=str(message.timestamp) + " UTC")
                    user = [m for m in message.server.members if m.id == mention.id][0]
                    try:
                        await self.bot.send_message(user, embed=emb)
                    except discord.Forbidden:
                        log.warning(
                            "Attempted to send a message to user with id {} "
                            "but failed due to permissions!".format(user.id)
                        )
                    except discord.NotFound:
                        log.warning(
                            "Destination not found!"
                        )
                    except discord.InvalidArgument:
                        log.warning(
                            "Invalid destination!"
                        )
                    except discord.HTTPException:
                        log.warning(
                            "Something went wrong!"
                        )
                    else:
                        return
        if message.content:
            for user in list(self.settings.keys()):
                if "words" in self.settings[user] and\
                        message.channel.id in self.settings[user]["words"]\
                        and self.settings[user]["words"][message.channel.id]:
                    for word in self.settings[user]["words"][message.channel.id]:
                        if word in message.content and user != message.author.id:
                            emb = discord.Embed(
                                title="A word you're subscribed to was used!",
                                description=message.content
                            )
                            emb.add_field(
                                name="Message author",
                                value="{}#{}".format(
                                    message.author.name,
                                    message.author.discriminator
                                ),
                                inline=False
                            )
                            emb.add_field(
                                name="Server",
                                value=message.server.name,
                                inline=False
                            )
                            emb.add_field(
                                name="Channel",
                                value=message.channel.name,
                                inline=False
                            )
                            emb.set_footer(
                                text=str(message.timestamp) + " UTC"
                            )
                            user = [m for m in message.server.members if m.id == user][0]
                            try:
                                await self.bot.send_message(user, embed=emb)
                            except discord.Forbidden:
                                log.warning(
                                    "Attempted to send a message to user with id {} "
                                    "but failed due to permissions!".format(user.id)
                                )
                            except discord.NotFound:
                                log.warning(
                                    "Destination not found!"
                                )
                            except discord.InvalidArgument:
                                log.warning(
                                    "Invalid destination!"
                                )
                            except discord.HTTPException:
                                log.warning(
                                    "Something went wrong!"
                                )
                            else:
                                return


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
