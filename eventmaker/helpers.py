from datetime import timedelta
import discord

from redbot.core.bot import Red

async def allowed_to_create(
        bot: Red, member: discord.Member, 
        role: discord.Role, guild: discord.Guild
):
    if member == guild.owner:
        return True
    elif await bot.is_mod(member):
        return True
    elif member.top_role in sorted(guild.roles)[role.position:]:
        return True
    else:
        return False


def parse_time(cur_time, msg: discord.Message):
    """Parse the time"""
    w = 0
    d = 0
    h = 0
    m = 0
    s = 0
    pieces = msg.content.split()
    for piece in pieces:
        if piece.endswith("w"):
            try:
                w = int(piece[:-1])
            except ValueError:
                return None  # issue with the user's input
        elif piece.endswith("d"):
            try:
                d = int(piece[:-1])
            except ValueError:
                return None  # issue with the user's input
        elif piece.endswith("h"):
            try:
                h = int(piece[:-1])
            except ValueError:
                return None  # issue with the user's input
        elif piece.endswith("m"):
            try:
                m = int(piece[:-1])
            except ValueError:
                return None  # issue with the user's input
        elif piece.endswith("s"):
            try:
                s = int(piece[:-1])
            except ValueError:
                return None  # issue with the user's input
        else:
            return None  # something went wrong in user's input
        return cur_time + timedelta(weeks=w, days=d, hours=h, minutes=m, seconds=s).total_seconds()