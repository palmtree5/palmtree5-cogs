from .banrole import BanRole


def setup(bot):
    bot.add_cog(BanRole(bot))
