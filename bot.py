import discord
from discord.commands import Option

import json

intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(
    intents=intents,
    members=True
)


@bot.event
async def on_ready():
    print(f"{bot.user} ist online")


@bot.event
async def on_member_join(member):
    category = discord.utils.get(member.guild.categories, name="Channel")
    channel = await member.guild.create_text_channel(str(member.name), category=category)
    if discord.utils.get(member.guild.channels, name=str(member.name)) is None:
        await channel.set_permissions(member, read_messages=True, send_messages=True, reason="User joined, Text Channel created")
        await channel.set_permissions(member.guild.default_role, read_messages=False, send_messages=False, reason="User joined, Text Channel created")
    else:
        log_channel = discord.utils.get(member.guild.channels, name="・logs・")
        await log_channel.send(f"Der Textkanal von {member.name} wurde bereits erstellt")
        return
    

    embed = discord.Embed(
        title=f"Textkanal von {member.name} wurde erfolgreich erstellt",
        description=f"Der Textkanal von {member.name} wurde erfolgreich erstellt",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    textchannel = discord.utils.get(member.guild.channels, name="・logs・")
    await textchannel.send(embed=embed)

@bot.slash_command(description="Erstellt einen Textkanal")
async def createchannel(ctx, user: Option(discord.Member, default=None)):
    category = discord.utils.get(ctx.guild.categories, name="Channel")
    channel = await ctx.guild.create_text_channel(str(user.name), category=category)
    if discord.utils.get(ctx.guild.channels, name=str(user.name)) is None:
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


def getToken():
    with open('token.json', 'r') as f:
        token = json.load(f)
        return token['token']
    

bot.run(getToken())
