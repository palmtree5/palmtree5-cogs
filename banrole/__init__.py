from .banrole import BanRole
import asyncio


def setup(bot):
    obj = bot.add_cog(BanRole(bot))
    if asyncio.iscoroutine(obj):
        await obj
