from .catfact import Catfact


def setup(bot):
    bot.add_cog(Catfact(bot))
