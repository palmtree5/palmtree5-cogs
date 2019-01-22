import sys


def setup(bot):
    if sys.version_info < (3, 6, 0):
        raise RuntimeError("This cog requires Python 3.6")
    from .hpapi import Hpapi

    n = Hpapi(bot)
    bot.add_cog(n)
