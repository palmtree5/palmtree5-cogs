from datetime import datetime
from urllib.parse import quote
import math
import datetime
from aiopixel.models.boosters import Booster
from aiopixel.models.players import Player
from aiopixel.models.friends import Friend
from aiopixel.models.guilds import Guild
import discord


async def get_booster_embed(booster: Booster) -> discord.Embed:
    game_name = booster.game_type.clean_name
    purchaser = await booster.purchaser_name()
    desc = "Activated at {}".format(booster.activated_at.strftime("%Y-%m-%d %H:%M:%S"))
    thumb_url = "http://minotar.net/avatar/{}/128.png".format(purchaser)
    remaining = str(datetime.timedelta(seconds=booster.length))
    embed = discord.Embed(
        title="Booster info", url="https://store.hypixel.net/category/307502", description=desc
    )
    embed.add_field(name="Game", value=game_name)
    embed.add_field(name="Purchaser", value=purchaser)
    embed.add_field(name="Remaining Time", value=remaining)
    embed.set_thumbnail(url=thumb_url)
    return embed


async def get_player_embed(player: Player) -> discord.Embed:
    rank = player.rank.pretty_name

    title = "{}{}".format("[{}] ".format(rank) if rank else "", player.displayname)

    em = discord.Embed(title=title, url="https://hypixel.net/player/{}".format(player.displayname))

    em.add_field(name="Rank", value=rank if rank else "None")
    em.add_field(name="Level", value=str(round(player.network_level(), 2)))
    if player.most_recent_game_type is not None:
        em.add_field(name="Last Playing", value=player.most_recent_game_type.clean_name)
    if player.online():
        em.add_field(name="Online", value="Yes")
    try:
        first_login = player.first_login.strftime("%Y-%m-%d %H:%M:%S")
    except AttributeError:
        first_login = "Never"
    try:
        last_login = player.last_login.strftime("%Y-%m-%d %H:%M:%S")
    except AttributeError:
        last_login = "Never"
    em.add_field(
        name="First/Last login", value="{} / {}".format(first_login, last_login), inline=False
    )

    em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(player.displayname))
    return em


async def get_friend_embed(friend: Friend) -> discord.Embed:
    sender = await friend.sender_name()
    receiver = await friend.receiver_name()
    em = discord.Embed(title=f"Friendship between {sender} and {receiver}")
    em.add_field(name="Created at", value=friend.started.strftime("%Y-%m-%d %H:%M:%S"))
    return em


async def get_guild_embed(guild: Guild) -> discord.Embed:
    gmaster = [await m.name() for m in guild.members if m.rank == "GUILDMASTER"][0]
    gmaster_face = "http://minotar.net/avatar/{}/128.png".format(gmaster)
    em = discord.Embed(
        title=guild.name,
        url="https://hypixel.net/guilds/{}".format(quote(guild.name)),
        description="Created at {} UTC".format(guild.created.strftime("%Y-%m-%d %H:%M:%S")),
    )
    em.add_field(name="Guildmaster", value=gmaster, inline=False)
    em.add_field(name="Guild experience", value=str(guild.exp) if guild.exp else "0")
    em.add_field(name="Member count", value=str(len(guild.members)))
    em.set_thumbnail(url=gmaster_face)
    return em
