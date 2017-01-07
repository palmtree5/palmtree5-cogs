"""DAH Cog for Red-DiscordBot
   by palmtree5
"""
from random import shuffle
from asyncio import as_completed
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import discord
from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO


class DAH():
    """Cog for a game of dah"""
    def __init__(self, bot):
        self.bot = bot
        self.cards = dataIO.load_json("data/dah/cards.json")
        self.games = {}
        self.bank = bot.get_cog("Economy").bank
        self.executor = ThreadPoolExecutor()

    @commands.command(pass_context=True, no_pm=True)
    async def dahcreate(self, ctx):
        """Create a game of dah"""
        server = ctx.message.server.id
        author = ctx.message.author
        if server not in self.games:
            authorplayer = {
                "player": author,
                "score": 0,
                "hand": []
            }
            newgame = {
                "status": "pregame",
                "gameowner": author,
                "settings": {
                    "join_inprogress": True,
                    "max_players": 8,
                    "win_score": 10,
                    "turn_timeout": 60,
                    "game_channel": None,
                    "sets": ["Base"],
                    "economy": 0
                },
                "players": [authorplayer]
            }
            self.games[server] = newgame
            await self.bot.say("Game created! Players can join by doing " +
                               "[p]dahjoin")
        else:
            await self.bot.say("A game has already been " +
                               "created in your server!")

    @commands.command(pass_context=True)
    async def dahcancel(self, ctx):
        """Cancels a dah game that is in pregame"""
        author = ctx.message.author
        server = ctx.message.server.id
        if server in self.games:
            game = self.games[server]
            if game["gameowner"] is author:
                self.games.pop(server)
                await self.bot.say("That game has been removed")
            else:
                await self.bot.say("You are not the owner of that game!")
        else:
            await self.bot.say("I can't delete a game that doesn't exist!")

    @commands.command(pass_context=True)
    async def dahstart(self, ctx):
        """Starts the game for the server"""
        author = ctx.message.author
        server = ctx.message.server.id
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                if game["gameowner"] is author:
                    if game["settings"]["game_channel"] is None:
                        game["settings"]["game_channel"] = ctx.message.channel
                    game["status"] = "inprogress"
                    self.games["server"] = game
                    await self.bot.say("Starting the game")
                    await self.dahgameloop(ctx, game)
                    for player in self.games[server]["players"]:
                        if self.bank.account_exists(player["player"]):
                            self.bank.deposit_credits(
                                player["player"],
                                player["score"] * game["settings"]["economy"]
                            )
                    self.games[ctx.message.server.id].pop()
            else:
                await self.bot.say("It looks like that game is " +
                                   "already in progress!")
        else:
            await self.bot.say("It looks like no game has been started " +
                               "for that server! Why don't you look at " +
                               ctx.prefix + "dahcreate for more on starting" +
                               " games?")

    @commands.command(pass_context=True)
    async def dahjoin(self, ctx):
        """Join a dah game"""
        server = ctx.message.server.id
        player = ctx.message.author
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                for plr in game["players"]:
                    if plr["player"] is player:
                        await self.bot.say("You are already in the game " +
                                           player.mention)
                        break
                else:  # Runs if the player hasn't already joined
                    entrant = {
                        "player": player,
                        "score": 0,
                        "hand": []
                    }
                    game["players"].append(entrant)
                    await self.bot.say("You have joined the game " +
                                       player.mention)
            elif game["status"] == "inprogress"\
                    and game["settings"]["join_inprogress"]:
                for plr in game["players"]:
                    if plr["player"] is player:
                        await self.bot.say("You are already in the game " +
                                           player.mention)
                        break
                else:  # Runs if the player hasn't already joined
                    entrant = {
                        "player": player,
                        "score": 0,
                        "hand": []
                    }
                    game["players"].append(entrant)
                    await self.bot.say("You have joined the game " +
                                       player.mention)
            else:
                await self.bot.say("Sorry, I can't do that")
        else:
            await self.bot.say("Sorry, it appears a game has not been " +
                               "started for that server!")

    @commands.command(pass_context=True)
    async def dahleave(self, ctx):
        """Allow someone in the game to leave it"""
        author = ctx.message.author
        server = ctx.message.server.id
        entrant = None
        if server in self.games:
            game = self.games[server]
            if game["gameowner"] is author:
                await self.bot.say("I can't do that because " +
                                   "you're the game owner!")
            else:
                if game["status"] == "pregame":
                    for player in game["players"]:
                        if player["player"] is author:
                            entrant = player
                            break
                    else:
                        await self.bot.say("You are not in the game!")
                        return
                    game["players"].pop(entrant)
                    await self.bot.say("OK " + author.mention + ", you" +
                                       " have been removed from the game")
        else:
            await self.bot.say("No game exists for this server!")

    @commands.group(pass_context=True)
    async def dahset(self, ctx):
        """Settings command for a dah game"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @dahset.command(pass_context=True, name="gamechannel")
    async def dahs_gamechannel(self, ctx, channel: discord.Channel):
        """Sets the channel to use for the game"""
        author = ctx.message.author
        server = ctx.message.server.id
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                if game["gameowner"] is author:
                    game["settings"]["game_channel"] = channel
                    await self.bot.say("Game channel now set to #"
                                       + channel.name)
                else:
                    await self.bot.say("Sorry, you don't have permission " +
                                       "to change game settings because " +
                                       "you did not create the game!")
            else:
                await self.bot.say("Settings can't be changed mid-game!")
        else:
            await self.bot.say("It appears there isn't a game created for " +
                               "your server!")

    @dahset.command(pass_context=True, name="joininprogress")
    async def dahs_joininprogress(self, ctx, answer="no"):
        """Allow joining an in progress game"""
        author = ctx.message.author
        server = ctx.message.server.id
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                if game["gameowner"] is author:
                    if answer.lower() == "yes":
                        game["settings"]["join_inprogress"] = True
                        await self.bot.say("Joining in progress " +
                                           "is now allowed")
                    elif answer.lower() == "no":
                        game["settings"]["join_inprogress"] = False
                        await self.bot.say("Joining in progress " +
                                           "is now disabled")
                    else:
                        await self.bot.say("That isn't a valid " +
                                           "response for this")
                        return
                    self.games[server] = game
                else:
                    await self.bot.say("Sorry, you don't have permission " +
                                       "to change game settings because " +
                                       "you did not create the game!")
            else:
                await self.bot.say("Settings can't be changed mid-game!")
        else:
            await self.bot.say("It appears there isn't a game created for " +
                               "your server!")

    @dahset.command(pass_context=True, name="maxplayers")
    async def dahs_maxplayers(self, ctx, count: int):
        """Sets the max number of players allowed to join"""
        author = ctx.message.author
        server = ctx.message.server.id
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                if game["gameowner"] is author:
                    if count < 2:
                        await self.bot.say("Sorry, I can't do that")
                        return
                    else:
                        game["settings"]["max_players"] = count
                        self.games[server] = game
                        await self.bot.say("The max number of players " +
                                           "is now " + str(count))
                else:
                    await self.bot.say("Sorry, you don't have permission " +
                                       "to change game settings because " +
                                       "you did not create the game!")
            else:
                await self.bot.say("Settings can't be changed mid-game!")
        else:
            await self.bot.say("It appears there isn't a game created for " +
                               "your server!")

    @dahset.command(pass_context=True, name="winscore")
    async def dahs_winscore(self, ctx, score: int):
        """Sets the win score"""
        author = ctx.message.author
        server = ctx.message.server.id
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                if game["gameowner"] is author:
                    if score < 1:
                        await self.bot.say("Sorry, I can't do that")
                        return
                    else:
                        game["settings"]["win_score"] = score
                        self.games[server] = game
                        await self.bot.say("The win score is now " +
                                           str(score))
                else:
                    await self.bot.say("Sorry, you don't have permission " +
                                       "to change game settings because " +
                                       "you did not create the game!")
            else:
                await self.bot.say("Settings can't be changed mid-game!")
        else:
            await self.bot.say("It appears there isn't a game created for " +
                               "your server!")

    @dahset.command(pass_context=True, name="turntimeout")
    async def dahs_turntimeout(self, ctx, period: int):
        """Sets the timeout time for each turn"""
        author = ctx.message.author
        server = ctx.message.server.id
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                if game["gameowner"] is author:
                    if period < 30:
                        await self.bot.say("Sorry, I can't do that")
                        return
                    else:
                        game["settings"]["turn_timeout"] = period
                        self.games[server] = game
                        await self.bot.say("The tiemout is now " +
                                           str(period) + " seconds")
                else:
                    await self.bot.say("Sorry, you don't have permission " +
                                       "to change game settings because " +
                                       "you did not create the game!")
            else:
                await self.bot.say("Settings can't be changed mid-game!")
        else:
            await self.bot.say("It appears there isn't a game created for " +
                               "your server!")

    @dahset.command(pass_context=True, name="setselect")
    async def dahs_setselect(self, ctx):
        """Select sets for the game"""
        author = ctx.message.author
        server = ctx.message.server.id
        chosen_sets = []
        if server in self.games:
            game = self.games[server]
            if game["status"] == "pregame":
                if game["gameowner"] is author:
                    setlist = "Set list: \n"
                    for item in self.cards["order"]:
                        setlist += self.cards[item]["name"] + "\n"
                    setlist += "\nPlease enter your selections by entering " +\
                               "a comma separated list of numbers " +\
                               "or a range (e.g. 1-10,12,15-18): "
                    await self.bot.say(setlist)
                    msg =\
                        await self.bot.wait_for_message(
                            timeout=60, author=author,
                            channel=ctx.message.channel
                        )
                    split_msg = msg.content.split(",")
                    for item in split_msg:
                        split_item = item.split("-")
                        if len(split_item) == 2:
                            try:
                                chosen_sets.extend(
                                    self.cards["order"]
                                    [int(split_item[0]) - 1:int(split_item[1])]
                                )
                            except ValueError:
                                pass
                        elif len(split_item) == 1:
                            try:
                                chosen_sets.append(
                                    self.cards["order"][int(split_item[0])])
                            except ValueError:
                                pass
                    game["settings"]["sets"] = chosen_sets
                    await self.bot.say("The chosen sets have been selected!")
                else:
                    await self.bot.say("Sorry, you don't have permission " +
                                       "to change game settings because " +
                                       "you did not create the game!")
            else:
                await self.bot.say("Settings can't be changed mid-game!")
        else:
            await self.bot.say("It appears there isn't a game created for " +
                               "your server!")

    @checks.mod_or_permissions(manage_messages=True)
    @dahset.command(pass_context=True, name="economy")
    async def dahs_economy(self, ctx, count: int):
        """Set the amount of credits to be given per point at endgame"""
        if count >= 0:
            self.games[ctx.message.server.id]["settings"]["economy"] = count

    async def dahgameloop(self, ctx, game):
        """Game loop for a dah game"""
        have_winner = False
        chan = game["settings"]["game_channel"]
        valid_white_indices = []
        valid_black_indices = []
        deck_white_idx = 0
        deck_black_idx = 0
        # Create the decks
        for deck in game["settings"]["sets"]:
            valid_white_indices.extend(self.cards[deck]["white"])
            valid_black_indices.extend(self.cards[deck]["black"])
        # Shuffle the decks
        deck_white = valid_white_indices
        deck_black = valid_black_indices
        shuffle(deck_white)
        shuffle(deck_black)
        # Deal white cards
        players = game["players"]
        for player in players:
            while len(player["hand"]) < 10:
                player["hand"].append(deck_white[deck_white_idx])
                deck_white_idx += 1
        game["players"] = players
        self.games[ctx.message.server.id] = game
        # Start the game up
        next_chooser_idx = 0
        while not have_winner:
            # Deal black card
            cur_chooser = players[next_chooser_idx]["player"]
            next_chooser_idx += 1
            round_choices = []
            await self.bot.send_message(chan, "The current chooser is " +
                                        cur_chooser.mention)
            black_card_idx = deck_black[deck_black_idx]
            deck_black_idx += 1
            black_card = self.cards["blackCards"][black_card_idx]
            blk_card_text =\
                "```{}\nPick: {}```".format(black_card["text"],
                                            str(black_card["pick"]))
            blk_card_msg =\
                "This round's black card is: {}".format(blk_card_text)
            await self.bot.send_message(chan, blk_card_msg)
            # Choose cards
            tasks = []
            for player in game["players"]:
                if player["player"] is not cur_chooser:
                    task = partial(self.handdisplay, player, game, black_card)
                    task = self.bot.loop.run_in_executor(self.executor, task)
                    tasks.append(task)

            tasknum = len(tasks)
            await self.bot.send_message(
                chan,
                "Players, please choose the card(s) you are playing"
            )
            played_status = '%d players remaining' % (tasknum)
            played_status_msg = await self.bot.send_message(chan, played_status)
            for f in as_completed(tasks):
                tasknum -= 1
                player_choices = await f
                round_choices.append(player_choices)
                status = '%d players remaining' % (tasknum)
                played_status_msg =\
                    await self._robust_edit(played_status_msg, status)

            played_text = "The played cards are as follows: \n"
            for plr in round_choices:
                for card in plr["cards"]:
                    played_text += str(plr["hand"][card]) + "\n"
                played_text += "\n"
            await self.bot.send_message(chan, played_text.strip())
            await self.bot.send_message(chan,
                                        "Chooser, please choose the winner")
            win_msg =\
                await self.bot.wait_for_message(
                    timeout=game["settings"]["turn_timeout"],
                    author=cur_chooser,
                    channel=chan
                )
            if win_msg is None:
                await self.bot.send_message(chan, "No winner selected!")
            else:
                try:
                    winner_choice = int(win_msg.content) - 1
                    winner = round_choices[winner_choice]["player"]
                    for plr in game["players"]:
                        if plr["player"] is winner:
                            plr["score"] += 1
                            break
                except ValueError:
                    pass
            # Check scores
            for player in players:
                if player["score"] >= game["settings"]["win_score"]:
                    # We have a winner so do most endgame tasks short of
                    # popping the game's dict from the game list
                    have_winner = True
                    await self.bot.send_message(chan, "And the winner is " +
                                                player["player"].mention)
                    break
            else:
                # Deal white cards
                players = game["players"]
                for player in players:
                    while len(player["hand"]) < 10:
                        player["hand"].append(deck_white[deck_white_idx])
                        deck_white_idx += 1
                game["players"] = players
                self.games[ctx.message.server.id] = game

    async def handdisplay(self, player, game, black_card):
        """Display hand to player"""
        player_hand_text =\
            "```{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}```".format(
                self.cards["whiteCards"][player["hand"][0]],
                self.cards["whiteCards"][player["hand"][1]],
                self.cards["whiteCards"][player["hand"][2]],
                self.cards["whiteCards"][player["hand"][3]],
                self.cards["whiteCards"][player["hand"][4]],
                self.cards["whiteCards"][player["hand"][5]],
                self.cards["whiteCards"][player["hand"][6]],
                self.cards["whiteCards"][player["hand"][7]],
                self.cards["whiteCards"][player["hand"][8]],
                self.cards["whiteCards"][player["hand"][9]]
            )
        # Display hand to player
        msg = "Your hand:\n" + player_hand_text +\
            "\nPlease enter your choice as a comma " +\
            "separated list (e.g. 1,2 or 3,6)"
        await self.bot.send_message(player["player"], msg)
        choose_msg = await self.bot.wait_for_message(
            timeout=game["settings"]["turn_timeout"],
            author=player["player"],
            channel=player["player"]
        )
        card_choices = []
        if choose_msg is not None:
            card_choices = choose_msg.content.split(",")
            if len(card_choices) != black_card["pick"]:
                player_choices = {
                    "cards": [],
                    "player": player["player"]
                }
                return player_choices
            else:
                chosen_cards = []
                for opt in card_choices:
                    if opt.strip() == "1" or opt.strip() == "2" or\
                            opt.strip() == "3"\
                            or opt.strip() == "4"\
                            or opt.strip() == "5" or\
                            opt.strip() == "6"\
                            or opt.strip() == "7"\
                            or opt.strip() == "8" or\
                            opt.strip() == "9"\
                            or opt.strip() == "10":
                        chosen_cards.append(int(opt) - 1)
                    else:
                        break
                if len(chosen_cards) != black_card["pick"]:
                    player_choices = {
                        "cards": [],
                        "player": player["player"]
                    }
                    return player_choices
                else:
                    player_choices = {
                        "cards": chosen_cards,
                        "player": player["player"],
                        "hand": player["hand"]
                    }
                    for idx in chosen_cards:
                        player["hand"].pop(idx)
                    return player_choices
        else:
            player_choices = {
                "cards": [],
                "player": player["player"]
            }
            return player_choices

    async def _robust_edit(self, msg, text):
        """From downloader cog"""
        try:
            msg = await self.bot.edit_message(msg, text)
        except discord.errors.NotFound:
            msg = await self.bot.send_message(msg.channel, text)
        except:
            raise
        return msg


def setup(bot):
    bot.add_cog(DAH(bot))
