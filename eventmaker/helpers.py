from datetime import timedelta, datetime as dt
import discord
from redbot.core import RedContext

from redbot.core.bot import Red


async def allowed_to_edit(ctx: RedContext, event: dict) -> bool:
    if ctx.author.id == event["creator"]:
        return True
    elif await ctx.bot.is_mod(ctx.author):
        return True
    elif ctx.author == ctx.guild.owner:
        return True
    return False


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


def get_event_embed(ctx: RedContext, event: dict) -> discord.Embed:
    emb = discord.Embed(
        title=event["event_name"],
        description=event["description"],
    )
    emb.add_field(name="Created by",
                  value=discord.utils.get(ctx.bot.get_all_members(), id=event["creator"])
                  )

    created_delta_str = get_delta_str(dt.utcfromtimestamp(event["create_time"]), ctx.message.created_at)
    created_str = "{} ago (at {} UTC)".format(
        created_delta_str,
        dt.utcfromtimestamp(event["create_time"]).strftime("%Y-%m-%d %H:%M:%S")
    )

    start_delta_str = get_delta_str(ctx.message.created_at, dt.utcfromtimestamp(event["event_start_time"]))
    start_str = "In {} (at {} UTC)".format(
        start_delta_str,
        dt.utcfromtimestamp(event["event_start_time"]).strftime("%Y-%m-%d %H:%M:%S"))
    emb.add_field(name="Created", value=created_str, inline=False)
    emb.add_field(name="Starts", value=start_str, inline=False)
    emb.add_field(name="Event ID", value=str(event["id"]))
    emb.add_field(
        name="Participant count", value=str(len(event["participants"]))
    )
    return emb


def get_delta_str(t1: dt, t2: dt) -> str:
    delta = t2 - t1
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    fmt = "{h}h {m}m {s}s"
    if days:
        fmt = "{d}d " + fmt
    return fmt.format(d=days, h=hours, m=minutes, s=seconds)


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
