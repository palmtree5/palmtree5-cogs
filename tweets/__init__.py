from .tweets import Tweets
import asyncio


async def setup(bot):
    obj = bot.add_cog(Tweets(bot))
    if asyncio.iscoroutine(obj):
        await obj
