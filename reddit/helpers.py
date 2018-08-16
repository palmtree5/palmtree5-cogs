from datetime import datetime as dt
from redbot.core import commands
import aiohttp
import discord
from redbot.core.utils.embed import randomize_colour
import logging

from reddit.errors import RedditAPIError, AccessForbiddenError, NotFoundError


async def make_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: dict = None,
    data: dict = None,
    params: dict = None,
    auth: aiohttp.BasicAuth = None,
):
    async with session.request(
        method, url, headers=headers, data=data, params=params, auth=auth, allow_redirects=False
    ) as resp:
        if resp.status == 403:
            raise AccessForbiddenError("I do not have access to that.")
        elif resp.status == 404 or resp.status == 302:
            # 302 will happen if the subreddit name meets the
            # requirements, but the subreddit doesn't exist
            raise NotFoundError("That does not appear to exist.")
        elif resp.status != 200:
            raise RedditAPIError("An error occurred. Status code: {}".format(resp.status))
        return await resp.json()


def post_embed(data: dict, now: dt) -> discord.Embed:
    created_at = dt.utcfromtimestamp(data["data"]["created_utc"])
    created_at_str = get_delta_str(created_at, now)
    if data["data"]["link_flair_text"] is not None:
        title = "[{}] {}".format(data["data"]["link_flair_text"], data["data"]["title"])
    else:
        title = data["data"]["title"]
    if "selftext" in data["data"] and data["data"]["selftext"] != "":
        desc = data["data"]["selftext"]
        if len(desc) > 2048:
            desc = desc[:2044] + "..."
    else:
        desc = data["data"]["domain"]
    em = discord.Embed(title=title, url=data["data"]["url"], description=desc)
    em = randomize_colour(em)
    em.add_field(name="Author", value=data["data"]["author"])
    em.add_field(
        name="Created",
        value="{} ago (at {} UTC)".format(
            created_at_str, created_at.strftime("%Y-%m-%d %H:%M:%S")
        ),
    )
    if data["data"]["stickied"]:
        em.add_field(name="Stickied", value="Yes")
    else:
        em.add_field(name="Stickied", value="No")
    em.add_field(name="Comments", value=str(data["data"]["num_comments"]))
    return em


async def get_modmail_messages(
    cog, base_url: str, channel: discord.TextChannel, current_sub: dict
):
    url = base_url.format("/r/{}/about/message/inbox".format(current_sub["subreddit"]))
    headers = {
        "Authorization": "bearer " + cog.access_token,
        "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5",
    }
    response = await make_request(cog.session, "GET", url, headers=headers)
    resp_json = response["data"]["children"]
    need_time_update = False
    for message in resp_json:
        if message["data"]["created_utc"] > current_sub["timestamp"]:
            need_time_update = True
            created_at = dt.utcfromtimestamp(message["data"]["created_utc"])
            desc = "Created at " + created_at.strftime("%m/%d/%Y %H:%M:%S")
            em = discord.Embed(
                title=message["data"]["subject"],
                url="https://reddit.com/r/" + current_sub["subreddit"] + "/about/message/inbox",
                description="/r/" + current_sub["subreddit"],
            )
            em = randomize_colour(em)
            em.add_field(name="Sent at (UTC)", value=desc)
            em.add_field(name="Author", value=message["data"]["author"])
            em.add_field(name="Message", value=message["data"]["body"])
            await channel.send(embed=em)
        if message["data"]["replies"] != "":
            for m in message["data"]["replies"]["data"]["children"]:
                if m["data"]["created_utc"] > current_sub["timestamp"]:
                    need_time_update = True
                    created_at = dt.utcfromtimestamp(m["data"]["created_utc"])
                    desc = "Created at " + created_at.strftime("%m/%d/%Y %H:%M:%S")
                    em = discord.Embed(
                        title=m["data"]["subject"],
                        url="https://reddit.com/r/"
                        + current_sub["subreddit"]
                        + "/about/message/inbox",
                        description="/r/" + current_sub["subreddit"],
                    )
                    em = randomize_colour(em)
                    em.add_field(name="Sent at (UTC)", value=desc)
                    em.add_field(name="Author", value=m["data"]["author"])
                    em.add_field(name="Message", value=m["data"]["body"])
                    await channel.send(embed=em)
    return need_time_update


async def get_subreddit_posts(
    cog, base_url: str, channel: discord.TextChannel, subreddit: str, last_name: str
):
    url = base_url.format("/r/{}/new".format(subreddit))

    params = {"before": last_name, "limit": 100}

    headers = {
        "Authorization": "bearer " + cog.access_token,
        "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5",
    }
    try:
        response = await make_request(cog.session, "GET", url, headers=headers, params=params)
    except NotFoundError as e:
        await channel.send(str(e))
        return
    except AccessForbiddenError as e:
        await channel.send(str(e))
        return
    except RedditAPIError as e:
        await channel.send(str(e))
        return
    resp_json = response["data"]["children"]
    resp_json = sorted(resp_json, key=lambda x: x["data"]["created_utc"])
    new_last = None
    for post in resp_json:
        em = post_embed(post, dt.utcnow())
        await channel.send(embed=em)
        new_last = post["data"]["name"]
    return new_last


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
