from random import shuffle
from random import choice as randchoice
from asyncio import as_completed
import asyncio
import math
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import discord
from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO


class HiddenDictator():
    """A game made for Red-DiscordBot"""
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.executor = ThreadPoolExecutor()

    @commands.command(pass_context=True, no_pm=True)
    async def hdcreate(self, ctx):
        """Create a new Hidden Dictator game"""
        server = ctx.message.server.id
        author = ctx.message.author
        if server not in self.games:
            authorplayer = {
                "player": author,
                "role": "",
                "party": ""
            }
            newgame = {
                "status": "pregame",
                "gameowner": author,
                "players": [authorplayer],
                "policydeck": [
                    "Liberal",
                    "Liberal",
                    "Liberal",
                    "Liberal",
                    "Liberal",
                    "Liberal",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist",
                    "Fascist"
                ],
                "discardpile": [],
                "settings": {
                    "gamechannel": ctx.message.channel
                },
                "chancellor": None,
                "president": None,
                "prev_chancellor": None,
                "prev_president": None,
                "pres_idx": 0,
                "liberalenacted": 0,
                "fascistenacted": 0,
                "electiontracker": 0,
                "player_count": 0,
                "vetoactive": False,
                "investigated": [],
                "next_pres": None
            }
            self.games[server] = newgame
            await self.bot.say("Game created! Others may "
                               "join the game by doing [p]hdjoin")
        else:
            await self.bot.say("A game already exists for this server!")
    
    @commands.group(pass_context=True, no_pm=True)
    async def hdset(self, ctx):
        """Game settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
    
    @hdset.command(pass_context=True, no_pm=True)
    async def gamechannel(self, ctx, channel: discord.Channel):
        """Set the game channel"""
        self.games[ctx.message.server.id]["settings"]["gamechannel"] = channel
        await self.bot.say("Set the game channel")

    @commands.command(pass_context=True, no_pm=True)
    async def hdjoin(self, ctx):
        """Join a game of Hidden Dictator"""
        author = ctx.message.author
        server = ctx.message.server.id
        if author not in self.games[server]["players"]:
            if len(self.games[server]["players"]) <= 10:
                newplayer = {
                    "player": author,
                    "role": "",
                    "party": ""
                }
                self.games[server]["players"].append(newplayer)
                await self.bot.say("Joined the game!")
            else:
                await self.bot.say("That game is full already :(")
        else:
            await self.bot.say("You are already in that game!")

    @commands.command(pass_context=True, no_pm=True)
    async def hdstart(self, ctx):
        """Starts the Hidden Dictator game for the current server"""
        server = ctx.message.server.id
        game = self.games[server]
        player_count = len(game["players"])
        if player_count >= 5:
            await self.bot.say("Starting game...")
            player_list = game["players"]
            game["player_count"] = player_count
            game["players"] = []
            # Set the liberals for the game
            for i in range(math.floor(player_count/2) + 1):
                player = randchoice(player_list)
                player_list.remove(player)
                player["party"] = "Liberal"
                player["role"] = "Liberal"
                game["players"].append(player)
            # Choose the dictator
            dictator = randchoice(player_list)
            player_list.remove(dictator)
            dictator["party"] = "Fascist"
            dictator["role"] = "Hitler"
            game["players"].append(dictator)
            # Make the remaining players fascists
            while player_list:
                player = player_list[0]
                player_list.remove(player)
                player["party"] = "Fascist"
                player["role"] = "Fascist"
                game["players"].append(player)

            shuffle(game["policydeck"])
            shuffle(game["players"])
            game["president"] = game["players"][0]["player"]
            game["pres_idx"] += 1

            await self.hdgameloop(ctx, game)  # Handoff to game loop
        else:
            await self.bot.say("Sorry, I cannot start the game until there's a minimum of 5 players joined")

    async def hdgameloop(self, ctx, game):
        """Game loop for games"""
        if game["next_pres"] is not None:
            game["president"] = game["next_pres"]
            game["next_pres"] = None
        else:
            game["president"] = game["players"][0]["player"]
            game["pres_idx"] += 1
        game_round = discord.Embed(title="Current Round")
        game_round.add_field(name="President", value=game["president"])

        # President nominates a chancellor
        await self.bot.send_message(
            "President " + game["president"].mention +
            ", please mention your nominee for chancellor"
        )
        def nomcheck(msg):
            if len(game["players"]) > 5:
                if msg.mentions[0] != game["prev_president"] and msg.mentions[0] != game["prev_chancellor"]:
                    return True
            elif len(game["players"]) <= 5:
                if msg.mentions[0] != game["prev_chancellor"]:
                    return True
        chancellor_nom =\
            await self.bot.wait_for_message(
                author=game["president"],
                channel=game["settings"]["gamechannel"],
                check=nomcheck
            )
        chancellor_nominee = chancellor_nom.mentions[0]
        tasks = []
        for player in game["players"]:
            task = partial(self.conduct_vote, player)
            task = self.bot.loop.run_in_executor(self.executor, task)
            tasks.append(task)
        tasknum = len(tasks)
        msg = "Players, you are voting whether to elect President {} and Chancellor {}.".format(game["president"].mention, chancellor_nominee.mention)
        await self.bot.send_message(game["settings"]["gamechannel"], msg)
        yeas = 0
        nays = 0
        votes = []
        for f in as_completed(tasks):
            tasknum -= 1
            vote = await f
            votes.append(vote)
        for v in votes:
            if v["vote"] == "Ja":
                yeas += 1
            else:
                nays += 1
        if yeas > nays:  # Successful election
            hitler = [p for p in game["players"] if p["role"] == "Hitler"][0]
            await self.bot.say(game["settings"]["gamechannel"], "President {} and Chancellor {} have been elected".format(game["president"].mention, chancellor_nominee.mention))
            if chancellor_nominee == hitler["player"] and game["fascistenacted"] >= 3:
                await self.bot.send_message(game["settings"]["gamechannel"], "Sadly for you Liberals, Hitler was just elected Chancellor. Fascists, you win the game")
                return
            else:
                pres_hand = []
                for i in range(3):
                    pres_hand.append(game["policydeck"].pop(0))
                def check(msg):
                    if int(msg.content) == 1 or int(msg.content) == 2 or int(msg.content) == 3:
                        return True
                await self.bot.send_message(game["president"], "Please choose the policy you wish to discard (1, 2, or 3): {} {} {}".format(pres_hand[0], pres_hand[1], pres_hand[2]))
                discard_choice = await self.bot.wait_for_message(
                    author=game["president"],
                    channel=game["president"],
                    check=check
                )
                discarded = pres_hand.pop(int(discard_choice.content) - 1)
                game["discardpile"].append(discarded)
                if len(game["policydeck"]) < 3:
                    game["policydeck"].extend(game["discardpile"])
                    game["discardpile"] = []
                    shuffle(game["policydeck"])
                def check2(msg):
                    if int(msg.content) == 1 or int(msg.content) == 2:
                        return True
                if not game["vetoactive"]:
                    await self.bot.send_message(chancellor_nominee, "Chancellor, please choose the policy to enact (1 or 2): {} {}").format(pres_hand[0], pres_hand[1])
                    enact_choice = await self.bot.wait_for_message(
                        author= chancellor_nominee,
                        channel=chancellor_nominee,
                        check=check2
                    )
                    enacted_policy = pres_hand[int(enact_choice.content) - 1]
                    if enacted_policy == "Liberal":
                        game["liberalenacted"] += 1
                    else:
                        game["fascistenacted"] += 1
                else:
                    def check3(msg):
                        if int(msg.content) == 1 or int(msg.content) == 2 or msg.content.lower().startswith("veto"):
                            return True
                    await self.bot.send_message(chancellor_nominee, "Chancellor, please choose the policy to enact (1 or 2): {} {}").format(pres_hand[0], pres_hand[1])
                    enact_choice = await self.bot.wait_for_message(
                        author= chancellor_nominee,
                        channel=chancellor_nominee,
                        check=check3
                    )
                    if enact_choice.lower().startswith("veto"):
                        def check4(msg):
                            if msg.content.lower().startswith("yes") or msg.content.lower().startswith("no"):
                                return True
                        await self.bot.send_message(game["settings"]["gamechannel"], "The chancellor wishes to veto the agenda. President, please enter yes to agree to the veto or no to disagree")
                        veto_opt = await self.bot.wait_for_message(
                            author=game["president"],
                            channel=game["settings"]["gamechannel"],
                            check=check4
                        )
                        if veto_opt.lower().startswith("yes"):
                            game["electiontracker"] += 1
                            if game["electiontracker"] == 3:
                                game["prev_president"] = None
                                game["prev_chancellor"] = None
                                card = game["policydeck"].pop(0)
                                if card == "Liberal":
                                    game["liberalenacted"] += 1
                                else:
                                    game["fascistenacted"] += 1
                                if len(game["policydeck"]) < 3:
                                    game["policydeck"].extend(game["discardpile"])
                                    game["discardpile"] = []
                                    shuffle(game["policydeck"])
                                have_win = await self.check_policycount_win_conditions(game)
                                if have_win:
                                    return
                    else:
                        enacted_policy = pres_hand[int(enact_choice.content) - 1]
                        if enacted_policy == "Liberal":
                            game["liberalenacted"] += 1
                        else:
                            game["fascistenacted"] += 1
                presidential_powers_check = await self.check_presidential_powers(game)
                have_win = await self.check_policycount_win_conditions(game)
                if have_win or presidential_powers_check:
                    return
        else:
            await self.bot.send_message(game["settings"]["gamechannel"], "This government was not elected")
            game["electiontracker"] += 1
            if game["electiontracker"] == 3:
                game["prev_president"] = None
                game["prev_chancellor"] = None
                card = game["policydeck"].pop(0)
                if card == "Liberal":
                    game["liberalenacted"] += 1
                else:
                    game["fascistenacted"] += 1
                if len(game["policydeck"]) < 3:
                    game["policydeck"].extend(game["discardpile"])
                    game["discardpile"] = []
                    shuffle(game["policydeck"])
                have_win = await self.check_policycount_win_conditions(game)
                if have_win:
                    return

    async def check_presidential_powers(self, game):
        """Check for presidential powers"""
        def validplayer(msg):
            if msg.mentions[0] in game["players"]:
                return True
        def validinvestigate(msg):
            if msg.mentions[0] in game["players"] and msg.mentions[0] not in game["investigated"]:
                return True
        if game["fascistenacted"] == 5:  # This happens at the same point regardless of player count
            game["vetoactive"] = True
        if game["player_count"] == 5 or game["player_count"] == 6:
            if game["fascistenacted"] == 3:
                viewcards = []
                viewcards.append(game["policydeck"][0])
                viewcards.append(game["policydeck"][1])
                viewcards.append(game["policydeck"][2])
                await self.bot.send_message(game["president"], "The top three cards on the policy deck are: {} {} {}").format(viewcards[0], viewcards[1], viewcards[2])
            elif game["fascistenacted"] == 4 or game["fascistenacted"] == 5:
                await self.bot.send_message(game["settings"]["gamechannel"], "President, you must choose a player to kill. Please mention that player now")
                death_choice = await self.bot.wait_for_message(author=game["president"], channel=game["settings"]["gamechannel"], check=validplayer)
                await self.bot.send_message(game["settings"]["gamechannel"], "The president has chosen to kill {}".format(death_choice.mentions[0].mention))
                eliminate = [p for p in game["players"] if p["player"] == death_choice.mentions[0]][0]
                game["players"].pop(game["players"].index(eliminate))
                if eliminate["role"] == "Hitler":
                    await self.bot.send_message(game["settings"]["gamechannel"], "Liberals win due to eliminating Hitler!")
                    return True
        elif game["player_count"] == 7 or game["player_count"] == 8:
            if game["fascistenacted"] == 2:
                await self.bot.send_message(game["settings"]["gamechannel"], "President, please choose someone to investigate by mentioning them")
                investigate_choice = await self.bot.wait_for_message(author=game["president"], channel=game["settings"]["gamechannel"], check=validinvestigate)
                selected = [p for p in game["players"] if p["player"] == investigate_choice.mentions[0]]
                game["investigated"].append(selected)
                await self.bot.send_message(game["president"], "The player you selected is a member of the {} party".format(selected["party"]))
            elif game["fascistenacted"] == 3:
                await self.bot.send_message(game["settings"]["gamechannel"], "President, please nominate the next president by mentioning them")
                pres_nom_choice = await self.bot.wait_for_message(author=game["president"], channel=game["settings"]["gamechannel"], check=validplayer)
                game["next_pres"] = pres_nom_choice.mentions[0]
            elif game["fascistenacted"] == 4 or game["fascistenacted"] == 5:
                await self.bot.send_message(game["settings"]["gamechannel"], "President, you must choose a player to kill. Please mention that player now")
                death_choice = await self.bot.wait_for_message(author=game["president"], channel=game["settings"]["gamechannel"], check=validplayer)
                await self.bot.send_message(game["settings"]["gamechannel"], "The president has chosen to kill {}".format(death_choice.mentions[0].mention))
                eliminate = [p for p in game["players"] if p["player"] == death_choice.mentions[0]][0]
                game["players"].pop(game["players"].index(eliminate))
                if eliminate["role"] == "Hitler":
                    await self.bot.send_message(game["settings"]["gamechannel"], "Liberals win due to eliminating Hitler!")
                    return True
        elif game["player_count"] == 9 or game["player_count"] == 10:
            if game["fascistenacted"] == 1 or game["fascistenacted"] == 2:
                await self.bot.send_message(game["settings"]["gamechannel"], "President, please choose someone to investigate by mentioning them")
                investigate_choice = await self.bot.wait_for_message(author=game["president"], channel=game["settings"]["gamechannel"], check=validinvestigate)
                selected = [p for p in game["players"] if p["player"] == investigate_choice.mentions[0]]
                game["investigated"].append(selected)
                await self.bot.send_message(game["president"], "The player you selected is a member of the {} party".format(selected["party"]))
            elif game["fascistenacted"] == 3:
                await self.bot.send_message(game["settings"]["gamechannel"], "President, please nominate the next president by mentioning them")
                pres_nom_choice = await self.bot.wait_for_message(author=game["president"], channel=game["settings"]["gamechannel"], check=validplayer)
                game["next_pres"] = pres_nom_choice.mentions[0]
            elif game["fascistenacted"] == 4 or game["fascistenacted"] == 5:
                await self.bot.send_message(game["settings"]["gamechannel"], "President, you must choose a player to kill. Please mention that player now")
                death_choice = await self.bot.wait_for_message(author=game["president"], channel=game["settings"]["gamechannel"], check=validplayer)
                await self.bot.send_message(game["settings"]["gamechannel"], "The president has chosen to kill {}".format(death_choice.mentions[0].mention))
                eliminate = [p for p in game["players"] if p["player"] == death_choice.mentions[0]][0]
                game["players"].pop(game["players"].index(eliminate))
                if eliminate["role"] == "Hitler":
                    await self.bot.send_message(game["settings"]["gamechannel"], "Liberals win due to eliminating Hitler!")
                    return True
        return False

    async def check_policycount_win_conditions(self, game):
        """Checks win conditions for the game"""
        if game["liberalenacted"] == 5:
            await self.bot.send_message(game["settings"]["gamechannel"], "Liberals win!")
            return True
        elif game["fascistenacted"] == 6:
            await self.bot.send_message(game["settings"]["gamechannel"], "Fascists win!")
            return True

    async def conduct_vote(self, player):
        msg = "Enter \"Ja\" to elect the current government or \"Nein\" to vote against it"
        await self.bot.send_message(player["player"], msg)
        def check(msg):
            return "ja" in msg.content.lower() or "nein" in msg.content.lower()
        vote_msg = await self.bot.wait_for_message(
            author=player["player"],
            channel=player["player"],
            check=check
        )
        if vote_msg.text.lower() == "ja":
            ret = {
                "player": player,
                "vote": "Ja"
            }
            return ret
        else:
            ret = {
                "player": player,
                "vote": "Nein"
            }
            return ret


def setup(bot):
    """Setup function"""
    n = HiddenDictator(bot)
    bot.add_cog(n)
