import sys

from redbot.core import data_manager


def setup(bot):
    if sys.version_info < (3, 6, 0):
        raise RuntimeError("This cog requires Python 3.6")
    from .hpapi import Hpapi
    n = Hpapi(bot)
    data_manager.load_bundled_data(n, __file__)
    bot.add_cog(n)
