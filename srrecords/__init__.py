from .srrecords import SRRecords


def setup(bot):
    n = SRRecords(bot)
    bot.add_cog(n)