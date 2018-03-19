from .slowmode import SlowMode


def setup(bot):
    bot.add_cog(SlowMode(bot))
