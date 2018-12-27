import aiohttp
import discord
import asyncio
from fnmatch import fnmatch
from redbot.core.bot import Red
from redbot.core import commands, checks, Config

GH_API = "https://api.github.com/graphql"

class GHC:
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.db = Config.get_conf(self, identifier=59595922, force_registration=True)
        self.session = aiohttp.ClientSession()
        default_global = {"token": ""}
        default_guild = {"cards": {}}
        self.db.register_global(**default_global)
        self.db.register_guild(**default_guild)
        self.colour = {
            'open': 0x6cc644,
            'closed': 0xbd2c00,
            'merged': 0x6e5494
        }
    
    def __unload(self):
        if not self.session.closed:
            fut = asyncio.ensure_future(self.session.close())
            yield from fut.__await__()

    @commands.group(aliases=["ghc"])
    async def githubcards(self, ctx: commands.Context):
        """Manage GithubCards"""
        pass
    
    @githubcards.command()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def add(self, ctx: commands.Context, prefix: str, github: str)
        """
        Add a new Github repo with the specified prefix.

        \"github\" argument must be in the format of \"username/repository\"
        """
        prefix = prefix.lower()
        exists = await self.db.guild(ctx.guild).cards.get_raw(prefix)
        if exists:
            await ctx.send("A repo already exists with that prefix!")
            return
        elif len(github.split("/")) != 2:
            await ctx.send("Invalid format. Use format Username/Repository")
            return
        else:
            token = await self.db.token()
            username, repository = github.split("/")
            async with self.session.post(
                GH_API,
                data="""
                {
                    repository(owner: {owner}, name: {repository}){
                        name
                    }
                }
                """.format(owner=username, repository=repository),
                headers={"Authorization": "Bearer {token}".format(token=token)}
            ) as r:
                data = await r.json()
                if data["data"]["repository"] is None and "errors" in data:
                    for error in data["errors"]:
                        if "type" in error and error["type"] == "NOT_FOUND":
                            await ctx.send(error["message"])
                            return
            new_card = {
                "username": username,
                "repository": repository,
                "fields": {
                    'author': True,
                    'status': True,
                    'comments': True,
                    'description': True,
                    'mergestatus': True,
                    'labels': True,
                    'closedby': False,
                    'locked': False,
                    'assigned': False,
                    'createdat': False,
                    'milestone': False,
                    'reviews': True
                }
            }
            await self.db.guild(ctx.guild).cards.set_raw(prefix, value=new_card)
            await ctx.send("Repo added!")
    
    @githubcards.command()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def remove(self, ctx: commands.Context, prefix: str):
        """Remove the repo with the specified prefix"""
        prefix = prefix.lower()
        data = await self.db.guild(ctx.guild).cards.get_raw(prefix)
        if data:
            await self.db.guild(ctx.guild).cards.clear_raw(prefix)
            await ctx.send("Repo removed!")
    
    
    @githubcards.command()
    @checks.is_owner()
    async def settoken(self, ctx: commands.Context, token: str)
        """
        Sets the token to be used for GithubCards

        Generate one by visiting https://github.com/settings/tokens/new
        """
        async with self.session.post(
            GH_API, data={"query": "{viewer {login}}"}, headers={"Authorization": "Bearer " + token}
        ) as r:
            if r.status != 200:
                await ctx.send("Something is wrong with that token. Please try again")
                return
        await self.db.token.set(token)
        await ctx.send("Token set successfully")

    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.abc.GuildChannel) and not message.author.bot:
            for word in message.content.split():
                cards = await self.db.guild(message.guild).cards()
                for prefix in cards:
                    if fnmatch(word.lower(), '{}#*'.format(prefix)):
                        pfx, num = word.split("#")
                        await self.post_issue_or_pr(message, pfx, num)

    
    async def post_issue_or_pr(self, message, prefix, number):
        card_data = await self.db.guild(message.guild).cards.get_raw(prefix)
        username = card_data["username"]
        repository = card_data["repository"]
        fields = card_data["fields"]
        token = await self.db.token()
        if not token:
            return
        async with self.session.post(
            GH_API,
            data={
                "query": """
                {
                    repository(owner: {username}, name: {repository}){
                        issueOrPullRequest(number: {number}){
                            __typename
                            ... on Issue {
                                url,
                                body,
                                author {
                                    login,
                                    url,
                                    avatarUrl
                                },
                                createdAt,
                                title,
                                comments(last: 10) {
                                    totalCount
                                },
                                state
                            }
                            ... on PullRequest {
                                url,
                                body,
                                author {
                                    login,
                                    url,
                                    avatarUrl
                                },
                                createdAt,
                                title,
                                comments(last: 10){
                                    totalCount
                                },
                                state,
                                mergeable,
                                merged,
                                mergedAt,
                                mergedBy {
                                    login
                                },
                                mergeCommit{
                                    commitUrl
                                }
                            }
                        }
                    }
                }"""
            },
            headers={"Authorization": "Bearer {token}".format(token=token)}
        ) as r:
            data = await r.json()
            if data["data"]["issueOrPullRequest"]:
                ipr = data["data"]["issueOrPullRequest"]
                if ipr["__typename"] == "Issue":
                    pass
                elif ipr["__typename"] == "PullRequest":
                    pass

    