from .hpapi import Hpapi
from redbot.core import data_manager
from pathlib import Path


def setup(bot):
    n = Hpapi()
    init_file = Path(__file__)
    print(init_file.is_file())
    print(init_file.parent)
    #print(package_folder.is_dir())
    data_manager.load_bundled_data(n, __file__)
    bot.add_cog(n)
