from .messagepinner import MessagePinner
import asyncio


def setup(bot):
    obj = bot.add_cog(MessagePinner())
    if asyncio.iscoroutine(obj):
        await obj
