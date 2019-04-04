from .tweets import Tweets
import asyncio


def setup(bot):
    obj = bot.add_cog(Tweets(bot))
    if asyncio.iscoroutine(obj):
        await obj
