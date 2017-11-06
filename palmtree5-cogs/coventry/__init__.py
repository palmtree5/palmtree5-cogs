from .coventry import Coventry


def setup(bot):
    bot.add_cog(Coventry(bot))
