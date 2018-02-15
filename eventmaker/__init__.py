from .eventmaker import EventMaker


def setup(bot):
    n = EventMaker(bot)
    bot.add_cog(n)
