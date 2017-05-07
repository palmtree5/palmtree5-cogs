from .eventmaker import EventMaker
import asyncio

def setup(bot):
    n = EventMaker(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.check_events())
    loop.create_task(n.server_data_check())
    bot.add_listener(n.server_join, "on_server_join")
    bot.add_listener(n.server_leave, "on_server_remove")
    bot.add_cog(n)
