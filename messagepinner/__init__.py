from .messagepinner import MessagePinner


def setup(bot):
    to_add = MessagePinner()
    bot.add_cog(to_add)
