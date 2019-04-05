from .srrecords import SRRecords
import asyncio


async def setup(bot):
    obj = bot.add_cog(SRRecords())
    if asyncio.iscoroutine(obj):
        await obj
