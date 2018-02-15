from datetime import datetime as dt

import asyncio
import discord
from redbot.core.context import RedContext
from redbot.core.utils.embed import randomize_colour

numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


async def booster_menu(ctx: RedContext, booster_list: list,
                       message: discord.Message=None,
                       page=0, timeout: int=30):
    """menu control logic for this taken from
       https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
    em = booster_list[page]
    if not message:
        message = await ctx.send(embed=em)
        await message.add_reaction("⬅")
        await message.add_reaction("❌")
        await message.add_reaction("➡")
    else:
        await message.edit(embed=em)

    def react_check(reaction, user):
        return user == ctx.author \
            and str(reaction.emoji) in ["➡", "⬅", "❌"]
    try:
        react, _ = await ctx.bot.wait_for(
            "reaction_add", timeout=timeout, check=react_check
        )
    except asyncio.TimeoutError:
        try:
            await message.clear_reactions()
        except discord.Forbidden:
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
        if page == len(booster_list) - 1:
            next_page = 0  # Loop around to the first item
        else:
            next_page = page + 1
        return await booster_menu(ctx, booster_list, message=message,
                                  page=next_page, timeout=timeout)
    elif react == "back":
        perms = message.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction("⬅", ctx.author)
            except discord.NotFound:
                pass
        if page == 0:
            next_page = len(booster_list) - 1  # Loop around to the last item
        else:
            next_page = page - 1
        return await booster_menu(ctx, booster_list, message=message,
                                  page=next_page, timeout=timeout)
    else:
        return await message.delete()


async def friends_menu(ctx: RedContext, friends_list: list,
                       message: discord.Message=None,
                       page=0, timeout: int=30):
    """menu control logic for this taken from
       https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
    s = friends_list[page]
    created_at = dt.utcfromtimestamp(s["time"])
    site_url = "https://www.hypixel.net/player/{}".format(s["name"])
    em = discord.Embed(title="Friends of {}".format(s["name"]),
                       url=site_url,
                       timestamp=created_at)
    em = randomize_colour(em)
    em.add_field(name="Name", value=str(s["fname"]))
    em.set_thumbnail(url="http://minotar.net/avatar/{}/128.png".format(s["fname"]))
    if not message:
        message = await ctx.send(embed=em)
        await message.add_reaction("⬅")
        await message.add_reaction("❌")
        await message.add_reaction("➡")
    else:
        await message.edit(embed=em)

    def react_check(reaction, user):
        return user == ctx.author \
            and str(reaction.emoji) in ["➡", "⬅", "❌"]
    try:
        react, _ = await ctx.bot.wait_for(
            "reaction_add", timeout=timeout, check=react_check
        )
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
        next_page = 0
        perms = message.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction("➡", ctx.author)
            except discord.NotFound:
                pass
        if page == len(friends_list) - 1:
            next_page = 0  # Loop around to the first item
        else:
            next_page = page + 1
        return await friends_menu(ctx, friends_list, message=message,
                                  page=next_page, timeout=timeout)
    elif react == "back":
        next_page = 0
        perms = message.channel.permissions_for(ctx.guild.me)
        if perms.manage_messages:  # Can manage messages, so remove react
            try:
                await message.remove_reaction("⬅", ctx.author)
            except discord.NotFound:
                pass
        if page == 0:
            next_page = len(friends_list) - 1  # Loop around to the last item
        else:
            next_page = page - 1
        return await friends_menu(ctx, friends_list, message=message,
                                  page=next_page, timeout=timeout)
    else:
        return await message.delete()
