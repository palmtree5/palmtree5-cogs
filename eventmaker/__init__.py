from .eventmaker import EventMaker
import asyncio


def setup(bot):
    obj = bot.add_cog(EventMaker(bot))
    if asyncio.iscoroutine(obj):
        await obj
