from .tweets import Tweets


def setup(bot):
    n = Tweets(bot)
    bot.add_cog(n)
