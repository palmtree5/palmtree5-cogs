from pathlib import Path
import sys
from .hpapi import Hpapi
import asyncio
import json

with open(Path(__file__).parent / "info.json") as infofile:  # Happen to like Jack's way of constructing this from what's in the info.json file so this is very much courtesy of him
    __red_end_user_data_statement__ = json.load(infofile)["end_user_data_statement"]

async def setup(bot):
    if sys.version_info < (3, 6, 0):
        raise RuntimeError("This cog requires Python 3.6")
    
    obj = bot.add_cog(Hpapi(bot))
    if asyncio.iscoroutine(obj):
        await obj
