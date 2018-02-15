import asyncio
import discord
from redbot.core.context import RedContext
from redbot.core.utils.embed import randomize_colour


numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


async def tweet_menu(ctx: RedContext, post_list: list,
                     message: discord.Message=None,
                     page=0, timeout: int=30):
    """menu control logic for this taken from
       https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
    s = post_list[page]
    created_at = s.created_at
    post_url =\
        "https://twitter.com/{}/status/{}".format(s.user.screen_name, s.id)
    desc = "Created at: {}".format(created_at)
    em = discord.Embed(title="Tweet by {}".format(s.user.name),
                       url=post_url,
                       description=desc)
    em = randomize_colour(em)
    em.add_field(name="Text", value=s.text)
    em.add_field(name="Retweet count", value=str(s.retweet_count))
    if hasattr(s, "extended_entities"):
        em.set_image(url=s.extended_entities["media"][0]["media_url"] + ":thumb")
    if not message:
        message =\
            await ctx.send(embed=em)
        await message.add_reaction("⬅")
        await message.add_reaction("❌")
        await message.add_reaction("➡")
    else:
        await message.edit(embed=em)

    def check_react(r, u):
        return u == ctx.author and r.emoji in ["➡", "⬅", "❌"]

    try:
        react, _ = await ctx.bot.wait_for(
            "reaction_add", timeout=timeout, check=check_react
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
        if page == len(post_list) - 1:
            next_page = 0  # Loop around to the first item
        else:
            next_page = page + 1
        return await tweet_menu(ctx, post_list, message=message,
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
            next_page = len(post_list) - 1  # Loop around to the last item
        else:
            next_page = page - 1
        return await tweet_menu(ctx, post_list, message=message,
                                page=next_page, timeout=timeout)
    else:
        return await message.delete()
