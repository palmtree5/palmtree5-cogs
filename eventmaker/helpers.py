import contextlib
from datetime import timedelta, datetime as dt
import discord
from redbot.core import commands
from redbot.core import commands, Config


async def allowed_to_edit(ctx: commands.Context, event: dict) -> bool:
    if not ctx.guild:
        return False
    if ctx.author.id == event["creator"]:
        return True
    elif await ctx.bot.is_mod(ctx.author):
        return True
    elif ctx.author == ctx.guild.owner:
        return True
    return False


def allowed_to_create():
    async def pred(ctx):
        if not ctx.guild:
            return False
        min_role_id = await ctx.cog.settings.guild(ctx.guild).min_role()
        if min_role_id == 0:
            min_role = ctx.guild.default_role
        else:
            min_role = discord.utils.get(ctx.guild.roles, id=min_role_id)
        if ctx.author == ctx.guild.owner:
            return True
        elif await ctx.bot.is_mod(ctx.author):
            return True
        elif ctx.author.top_role in sorted(ctx.guild.roles)[min_role.position :]:
            return True
        else:
            return False

    return commands.check(pred)


async def check_event_start(channel: discord.TextChannel, event: dict, config: Config):
    cur_time = dt.utcnow()
    guild = channel.guild
    if cur_time.timestamp() < event["event_start_time"] or event["has_started"]:
        return False, None
    event["has_started"] = True
    emb = get_event_embed(guild, cur_time, event)
    with contextlib.suppress(discord.Forbidden):
        if channel:
            await channel.send("Event starting now!", embed=emb)
    for user in [guild.get_member(m) for m in event["participants"] if guild.get_member(m)]:
        with contextlib.suppress(discord.Forbidden):
            if await config.member(user).dms():  # Only send to users who have opted into DMs
                await user.send("Event starting now!", embed=emb)

    return True, event


def get_event_embed(guild: discord.Guild, now: dt, event: dict) -> discord.Embed:
    emb = discord.Embed(title=event["event_name"], description=event["description"])
    emb.add_field(name="Created by", value=guild.get_member(event["creator"]))

    created_delta_str = get_delta_str(dt.utcfromtimestamp(event["create_time"]), now)
    created_str = "{} ago (at {} UTC)".format(
        created_delta_str, dt.utcfromtimestamp(event["create_time"]).strftime("%Y-%m-%d %H:%M:%S")
    )

    start_delta_str = get_delta_str(now, dt.utcfromtimestamp(event["event_start_time"]))
    if event["has_started"]:
        start_str = "Already started!"
    else:
        start_str = "In {} (at {} UTC)".format(
            start_delta_str,
            dt.utcfromtimestamp(event["event_start_time"]).strftime("%Y-%m-%d %H:%M:%S"),
        )
    emb.add_field(name="Created", value=created_str, inline=False)
    emb.add_field(name="Starts", value=start_str, inline=False)
    emb.add_field(name="Event ID", value=str(event["id"]))
    emb.add_field(name="Participant count", value=str(len(event["participants"])))
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
