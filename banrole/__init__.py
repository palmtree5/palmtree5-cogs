import json
from pathlib import Path
from .banrole import BanRole
import asyncio


with open(Path(__file__).parent / "info.json") as infofile:  # Happen to like Jack's way of constructing this from what's in the info.json file so this is very much courtesy of him
    __red_end_user_data_statement__ = json.load(infofile)["end_user_data_statement"]


async def setup(bot):
    obj = bot.add_cog(BanRole(bot))
    if asyncio.iscoroutine(obj):
        await obj
