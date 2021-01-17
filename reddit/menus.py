import asyncio

import discord
from redbot.core import commands

from .helpers import post_embed

numbs = {"next": "➡", "back": "⬅", "exit": "❌"}


async def post_menu(
    ctx: commands.Context,
    post_list: list,
    message: discord.Message = None,
    page=0,
    timeout: int = 30,
):
    """menu control logic for this taken from
       https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
    s = post_list[page]
    em = post_embed(s, ctx.message.created_at)

    if not message:
        message = await ctx.send(embed=em)
        await message.add_reaction("⬅")
        await message.add_reaction("❌")
        await message.add_reaction("➡")
    else:
        await message.edit(embed=em)

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
        try:
            perms = message.channel.permissions_for(ctx.guild.me)
        except AttributeError:
            perms = message.channel.permissions_for(ctx.bot.user)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction("➡", ctx.author)
            except discord.NotFound:
                pass
        if page == len(post_list) - 1:
            next_page = 0  # Loop around to the first item
        else:
            next_page = page + 1
        return await post_menu(ctx, post_list, message=message, page=next_page, timeout=timeout)
    elif react == "back":
        try:
            perms = message.channel.permissions_for(ctx.guild.me)
        except AttributeError:
            perms = message.channel.permissions_for(ctx.bot.user)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction("⬅", ctx.author)
            except discord.NotFound:
                pass
        if page == 0:
            next_page = len(post_list) - 1  # Loop around to the last item
        else:
            next_page = page - 1
        return await post_menu(ctx, post_list, message=message, page=next_page, timeout=timeout)
    else:
        return await message.delete()
