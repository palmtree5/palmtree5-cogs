from .messagepinner import MessagePinner


def setup(bot):
    to_add = MessagePinner()
    bot.add_listener(to_add.on_message, "on_message")
    bot.add_cog(to_add)
