from .lockdown import Lockdown
from redbot.core.bot import Red
import asyncio


async def setup(bot: Red):
    obj = bot.add_cog(Lockdown())
    if asyncio.iscoroutine(obj):
        await obj
