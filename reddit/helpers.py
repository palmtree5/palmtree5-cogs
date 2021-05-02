from datetime import datetime as dt
from redbot.core import commands
import discord
from redbot.core.utils.embed import randomize_colour
import asyncpraw
import asyncprawcore


async def get_subreddit(reddit: asyncpraw.Reddit, ctx: commands.Context, subreddit: str) -> asyncpraw.reddit.Subreddit:
    try:
        return await reddit.subreddit(subreddit, fetch=True)
    except asyncprawcore.exceptions.Forbidden:
        await ctx.send("That subreddit is a private subreddit I cannot read.")
        return None
    except asyncprawcore.exceptions.NotFound:
        await ctx.send(
            "That subreddit does not exist. If it previously existed, it may have been banned."
        )
        return None


def post_embed(post: asyncpraw.reddit.Submission, now: dt) -> discord.Embed:
    created_at = dt.utcfromtimestamp(post.created_utc)
    created_at_str = get_delta_str(created_at, now)
    if post.link_flair_text is not None:
        title = f"[{post.link_flair_text}] {post.title}"
    else:
        title = post.title
    if len(title) > 256:
        title = title[:252] + "..."
    if hasattr(post, "selftext") and post.selftext != "":
        desc = post.selftext
        if len(desc) > 2048:
            desc = desc[:2044] + "..."
    else:
        desc = post.domain
    em = discord.Embed(title=title, url=post.url, description=desc)
    em = randomize_colour(em)
    em.add_field(name="Author", value=f"[{post.author.name}](https://reddit.com/u/{post.author.name})")
    em.add_field(
        name="Created",
        value="{} ago (at {} UTC)".format(
            created_at_str, created_at.strftime("%Y-%m-%d at %H:%M:%S UTC")
        ),
    )
    if post.stickied:
        em.add_field(name="Stickied", value="Yes")
    else:
        em.add_field(name="Stickied", value="No")
    em.add_field(name="Comments", value=f"[{post.num_comments}]({post.permalink})")
    if post.thumbnail != "self":
        em.set_thumbnail(url=post.thumbnail)
    return em


def get_delta_str(t1: dt, t2: dt) -> str:
    delta = t2 - t1
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    fmt = "{h}h {m}m {s}s"
    if days:
        fmt = "{d}d " + fmt
    return fmt.format(d=days, h=hours, m=minutes, s=seconds)


def private_only():

    def predicate(ctx):
        if isinstance(ctx.channel, discord.abc.GuildChannel):
            raise commands.CheckFailure("This command cannot be used in guild channels.")
        return True

    return commands.check(predicate)


def get_color(sub: asyncpraw.reddit.Subreddit):
    if hasattr(sub, "primary_color") and sub.primary_color:
        return sub.primary_color
    elif hasattr(sub, "key_color") and sub.key_color:
        return sub.key_color
    else:
        return None