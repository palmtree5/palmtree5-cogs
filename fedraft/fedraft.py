from discord.ext import commands
from .utils.dataIO import dataIO
import discord
import math
from random import choice, shuffle


class FEDraft():
    """Character draft for FE games"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/fedraft/settings.json")

    @commands.command(pass_context=True)
    async def fedraft(self, ctx, game: str):
        """Starts the process of creating a character
           draft for the specified game. Will try
           to do the creation in a PM but will fall
           back to the channel the command was run
           in on failure to send a PM to the user
           Valid games are:
               bb - FE6
               bs - FE7
               ss - FE8
           More games may be added down the line"""
        use_pms = True
        author = ctx.message.author
        try:
            self.bot.send_message(
                author,
                "We will now walk through the process of setting options for the draft"
            )
        except discord.Forbidden:
            # Failed to DM the user for some reason, fall back to the channel the message is in
            use_pms = False
            self.bot.say("We will now walk through the process of setting options for the draft")
        if game == "bs" or game == "bb" or game == "ss":
            await self.fe_draft_generator(ctx, game, use_pms)
        else:
            await self.bot.say("That is not a valid game!")

    async def fe_draft_generator(self, ctx, game, use_pms=True):
        """Handles creating draft settings for FE7"""

        # Define wait_for_message checks

        def valid_route_check(msg):
            for route in list(game_data["chapters"].keys()):
                if route in msg.content.lower():
                    return True
            else:
                return False

        def gba_stats_check(msg):
            stats = msg.content.split(" ")
            for stat in stats:
                if stat != "Lv" and stat != "HP" and stat != "Str/Mag"\
                        and stat != "Skl" and stat != "Spd" and stat != "Lck"\
                        and stat != "Def" and stat != "Res" and stat != "Con"\
                        and stat != "Mov" and stat != "none":
                    return False
            return True

        def yn_check(msg):
            return "yes" in msg.content.lower() or "no" in msg.content.lower()

        def valid_prepro_check(msg):
            try:
                prepro_num = int(msg.content)
            except ValueError:
                return False
            return prepro_num <= game_data["prepro_count"]

        def diff_chk(msg):
            return "easy" in msg.content.lower() or "normal" in msg.content.lower() or "hard" in msg.content.lower()

        author = ctx.message.author
        draft_settings = {
            "game": game
        }
        game_data = dataIO.load_json("data/fedraft/" + self.settings[game])
        if use_pms:
            await self.bot.send_message(
                author,
                "Enter the route you will play ({}):".format(
                    " or ".join(list(game_data["chapters"].keys()))
                ))
            msg = await self.bot.wait_for_message(timeout=30, author=author, check=valid_route_check)
            if msg is None:
                await self.bot.send_message(author, "No input received!")
                return
            route = msg.content.lower()
            draft_settings["route"] = route
            await self.bot.send_message(
                author,
                "You may now choose to specify any average stats for characters. To do this,\n" +
                "enter the stats you would like to specify. These are the valid options:\n" +
                "```Lv HP Str/Mag Skl Spd Lck Def Res Con Mov```\nEnter them now, separated " +
                "by a space as they appear here (or type 'none' to skip this step):"
            )
            msg = await self.bot.wait_for_message(timeout=30, author=author, check=gba_stats_check)
            stats = msg.content.split(" ")
            for stat in stats:
                cur_stat = 0
                await self.bot.send_message(author, "Enter the average {}:".format(stat))
                msg = await self.bot.wait_for_message(timeout=30, author=author)
                try:
                    cur_stat = int(msg.content)
                except ValueError:
                    await self.bot.send_message(author, "Invalid input received!")
                    return
                draft_settings[stat] = cur_stat
            await self.bot.send_message(author, "Any preference on prepromotes (yes/no)?")
            msg = await self.bot.wait_for_message(timeout=30, author=author, check=yn_check)
            if msg is None:
                pass
            elif "yes" in msg.content.lower():
                await self.bot.send_message(
                    author,
                    "Enter the number of characters allowed to be prepromotes (max {}): ".format(
                        game_data["prepro_count"]
                    )
                )
                msg = await self.bot.wait_for_message(
                    timeout=30,
                    author=author,
                    check=valid_prepro_check
                )
                if msg is None:
                    await self.bot.send_message(author, "No input received!")
                    return
                draft_settings["prepro_count"] = msg.content
            await self.bot.send_message(
                author,
                "Select a difficulty (easy/normal/hard, does not correspond" +
                "to game difficulty, will affect number of characters given" +
                "by the generator): "
            )
            msg = await self.bot.wait_for_message(timeout=30, author=author, check=diff_chk)
            if msg is None:
                await self.bot.send_message(author, "No input received!")
                return
            draft_settings["difficulty"] = msg.content
            drafted = self.generate_draft(draft_settings)
            await self.bot.send_message(author, "Your picks: {}".format(" ".join(drafted)))
        else:
            await self.bot.send_message(
                ctx.message.channel,
                "I could not DM you! I need to be able to send you DMs for " +
                "you to use this command's functionality (to avoid spamming" +
                "a channel)")

    def generate_draft(self, draft_settings):
        """Actually does the picking"""
        data = dataIO.load_json("data/fedraft/" + self.settings[draft_settings["game"]])
        picks = data["chapters"][draft_settings["route"]]["required_characters"]
        if "prepro_count" in draft_settings:
            prepromotes_left = int(draft_settings["prepro_count"])
        else:
            prepromotes_left = data["prepro_count"]
        char_count = 0

        if draft_settings["difficulty"].lower() == "easy":
            char_count = math.ceil(data["max_bring"] * 1.1)
        elif draft_settings["difficulty"].lower() == "normal":
            char_count = data["max_bring"]
        elif draft_settings["difficulty"].lower() == "hard":
            char_count = math.floor(data["max_bring"] * 0.9)
        # Handle any prepromotes in the required character list
        for pick in picks:
            char_count -= 1
            if data["characters"][pick]["prepro"]:
                prepromotes_left -= 1
        while char_count > 0:
            char_list = list(data["characters"].keys())
            shuffle(char_list)
            next_char = choice(char_list)
            chap_list = data["chapters"][draft_settings["route"]]["ch_list"]
            shuffle(chap_list)
            chapter = choice(chap_list)
            if next_char not in picks:
                if chapter in data["chapters"][draft_settings["route"]]["recruitments"]\
                        and next_char in data["chapters"][draft_settings["route"]]["recruitments"][chapter]:
                    if data["characters"][next_char]["prepro"] and prepromotes_left > 0:
                        picks.append(next_char)
                        char_count -= 1
                        prepromotes_left -= 1
                    elif not data["characters"][next_char]["prepro"]:
                        picks.append(next_char)
                        char_count -= 1
        return picks


def setup(bot):
    n = FEDraft(bot)
    bot.add_cog(n)
