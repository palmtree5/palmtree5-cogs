import asyncio

import discord

numbs = {"next": "➡", "back": "⬅", "exit": "❌"}


async def event_menu(
    ctx, event_list: list, message: discord.Message = None, page=0, timeout: int = 30
):
    """menu control logic for this taken from
       https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
    emb = event_list[page]
    if not message:
        message = await ctx.send(embed=emb)
        await message.add_reaction("⬅")
        await message.add_reaction("❌")
        await message.add_reaction("➡")
    else:
        await message.edit(embed=emb)

    def react_check(r, u):
        return u == ctx.author and str(r.emoji) in ["➡", "⬅", "❌"]

    try:
        react, user = await ctx.bot.wait_for("reaction_add", check=react_check, timeout=timeout)
    except asyncio.TimeoutError:
        try:
            await message.clear_reactions()
        except discord.Forbidden:  # cannot remove all reactions
            await message.remove_reaction("⬅", ctx.guild.me)
            await message.remove_reaction("❌", ctx.guild.me)
            await message.remove_reaction("➡", ctx.guild.me)
        return None
    reacts = {v: k for k, v in numbs.items()}
    react = reacts[react.emoji]
    if react == "next":
        perms = message.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction("➡", ctx.author)
            except discord.NotFound:
                pass
        if page == len(event_list) - 1:
            next_page = 0  # Loop around to the first item
        else:
            next_page = page + 1
        return await event_menu(ctx, event_list, message=message, page=next_page, timeout=timeout)
    elif react == "back":
        perms = message.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction("⬅", ctx.author)
            except discord.NotFound:
                pass
        if page == 0:
            next_page = len(event_list) - 1  # Loop around to the last item
        else:
            next_page = page - 1
        return await event_menu(ctx, event_list, message=message, page=next_page, timeout=timeout)
    else:
        return await message.delete()
