from .reddit import Reddit


def setup(bot):
    bot.add_cog(Reddit(bot))
