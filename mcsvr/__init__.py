from .mcsvr import Mcsvr


def setup(bot):
    bot.add_cog(Mcsvr(bot))
