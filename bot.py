import discord
from discord.commands import Option

intents = discord.Intents.default()
bot = discord.Bot(
    intents=intents
)


@bot.event
async def on_ready():
    print(f"{bot.user} ist online")


@bot.event
async def on_member_join(ctx, user: Option(discord.Member, default=None)):
    category = discord.utils.get(ctx.guild.categories, name="Channel", category=category)
    channel = await ctx.guild.create_text_channel(str(user.name) + "'s - Channel")
    await channel.set_permissions(user, read_messages=True, send_messages=True, reason="User joined, Text Channel created")
    await channel.set_permissions(user.guild.default_role, read_messages=False, send_messages=False, reason="User joined, Text Channel created")

    embed = discord.Embed(
        title=f"Textkanal von {user.name} wurde erfolgreich erstellt",
        description=f"Der Textkanal von {user.name} wurde erfolgreich erstellt",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(url=user.display_avatar.url)
    textchannel = discord.utils.get(ctx.guild.channels, name="・logs・")
    await textchannel.send(embed=embed)
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(description="Erstellt einen Textkanal")
async def createchannel(ctx, user: Option(discord.Member, default=None)):
    category = discord.utils.get(ctx.guild.categories, name="Channel")
    channel = await ctx.guild.create_text_channel(str(user.name) + "'s - Channel", category=category)
    if discord.utils.get(ctx.guild.channels, name=str(user.name) + "'s - Channel") is None:
        await channel.set_permissions(user, read_messages=True, send_messages=True, reason="User joined, Text Channel created")
        await channel.set_permissions(user.guild.default_role, read_messages=False, send_messages=False, reason="User joined, Text Channel created")
    else:
        log_channel = discord.utils.get(ctx.guild.channels, name="・logs・")
        await log_channel.send(f"Der Textkanal von {user.name} wurde bereits erstellt")
        await ctx.respond("Dieser Textkanal existiert bereits", ephemeral=True)
        return
    

    embed = discord.Embed(
        title=f"Textkanal von {user.name} wurde erfolgreich erstellt",
        description=f"Der Textkanal von {user.name} wurde erfolgreich erstellt",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(url=user.display_avatar.url)
    textchannel = discord.utils.get(ctx.guild.channels, name="・logs・")
    await textchannel.send(embed=embed)
    await ctx.respond(embed=embed, ephemeral=True)
    

bot.run('MTA4MDI1MDcwNTc2OTY4MDkxNw.Gb4H1b.vVsUWlxKWRZg1jXeK14ASX2joytMoA7v-H2SQY')
