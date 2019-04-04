from .slowmode import SlowMode
import asyncio


def setup(bot):
    obj = bot.add_cog(SlowMode(bot))
    if asyncio.iscoroutine(obj):
        await obj
