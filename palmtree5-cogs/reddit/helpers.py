from datetime import datetime as dt
from discord.ext import commands
import aiohttp
import discord
from redbot.core.utils.embed import randomize_colour


async def make_request(
        session: aiohttp.ClientSession,
        method: str, url: str,
        headers: dict=None, data: dict=None,
        auth: aiohttp.BasicAuth=None):
    async with session.request(method, url, headers=headers, data=data, auth=auth) as resp:
        return await resp.json()


async def get_modmail_messages(
        cog, base_url: str, channel: discord.TextChannel, current_sub: dict):
    url = base_url.format(
        "/r/{}/about/message/inbox".format(
            current_sub["subreddit"]
        )
    )
    headers = {
        "Authorization": "bearer " + cog.access_token,
        "User-Agent": "Red-DiscordBotRedditCog/0.1 by /u/palmtree5"
    }
    response = await make_request(cog.session, "GET", url, headers=headers)
    resp_json = response["data"]["children"]
    need_time_update = False
    for message in resp_json:
        if message["data"]["created_utc"] > current_sub["timestamp"]:
            need_time_update = True
            created_at = dt.utcfromtimestamp(message["data"]["created_utc"])
            desc = "Created at " + created_at.strftime("%m/%d/%Y %H:%M:%S")
            em = discord.Embed(title=message["data"]["subject"],
                               url="https://reddit.com/r/"
                                   + current_sub["subreddit"]
                                   + "/about/message/inbox",
                               description="/r/"
                                           + current_sub["subreddit"])
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
                    em = discord.Embed(title=m["data"]["subject"],
                                       url="https://reddit.com/r/"
                                           + current_sub["subreddit"]
                                           + "/about/message/inbox",
                                       description="/r/"
                                                   + current_sub["subreddit"])
                    em = randomize_colour(em)
                    em.add_field(name="Sent at (UTC)", value=desc)
                    em.add_field(name="Author", value=m["data"]["author"])
                    em.add_field(name="Message", value=m["data"]["body"])
                    await channel.send(embed=em)
    return need_time_update

def private_only():
    def predicate(ctx):
        if isinstance(ctx.channel, discord.abc.GuildChannel):
            raise commands.CheckFailure("This command cannot be used in guild channels.")
        return True
    return commands.check(predicate)
