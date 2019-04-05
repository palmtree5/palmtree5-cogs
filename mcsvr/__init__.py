from .mcsvr import Mcsvr
import asyncio


async def setup(bot):
    obj = bot.add_cog(Mcsvr(bot))
    if asyncio.iscoroutine(obj):
        await obj
