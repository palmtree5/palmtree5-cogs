from .reddit import Reddit
import asyncio


async def setup(bot):
    obj = bot.add_cog(Reddit(bot))
    if asyncio.iscoroutine(obj):
        await obj
