from .ghc import GHC


def setup(bot):
    bot.add_cog(GHC(bot))