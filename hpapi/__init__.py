import sys
from .hpapi import Hpapi
import asyncio


def setup(bot):
    if sys.version_info < (3, 6, 0):
        raise RuntimeError("This cog requires Python 3.6")
    
    obj = bot.add_cog(Hpapi(bot))
    if asyncio.iscoroutine(obj):
        await obj
