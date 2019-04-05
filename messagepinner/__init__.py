from .messagepinner import MessagePinner
import asyncio


async def setup(bot):
    obj = bot.add_cog(MessagePinner())
    if asyncio.iscoroutine(obj):
        await obj
