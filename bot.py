import discord
from discord.commands import Option

import aiosqlite

import json

intents = discord.Intents.all()
intents.members = True
bot = discord.Bot(
    intents=intents,
    members=True,
    messages=True
)

DB = "user.db"


@bot.event
async def on_ready():
    print(f"{bot.user} ist online")

    async with aiosqlite.connect('user.db') as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY,
            channel_id INTEGER 
            )
            """
        )

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Wartet auf deine Bilder"))

async def create_user(user_id, channel_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO user (user_id, channel_id)
            VALUES (?, ?)
            """,
            (user_id, channel_id)
        )
        await db.commit()

def check_user(user_id, channel_id):
    with aiosqlite.connect(DB) as db:
        db.execute(
            """
            SELECT * FROM user WHERE user_id = ?
            """,
            (user_id,)
        )
        result = db.commit()
        if result is None:
            return create_user(user_id, channel_id)
        else:
            return True

# TODO: Create a function to check if the user has a channel

@bot.event
async def on_member_join(member):
    if check_user(member.id, channel.id):
        category = discord.utils.get(member.guild.categories, name="Channel")
        channel = await member.guild.create_text_channel(str(member.name), category=category)
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


@bot.event
async def on_message(message):
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(".png") or attachment.filename.endswith(".jpg") or attachment.filename.endswith(".jpeg") or attachment.filename.endswith(".gif"):
                link = attachment.url
                if ".png" in link:
                    index = link.index(".png")
                    new_link = link[:index+len(".png")]
                elif ".jpg" in link:
                    index = link.index(".jpg")
                    new_link = link[:index+len(".jpg")]
                elif ".jpeg" in link:
                    index = link.index(".jpeg")
                    new_link = link[:index+len(".jpeg")]
                elif ".gif" in link:
                    index = link.index(".gif")
                    new_link = link[:index+len(".gif")] 
                button = discord.ui.Button(label="Link", style=discord.ButtonStyle.primary, url=new_link)
                view = discord.ui.View()
                view.add_item(button)

                embed = discord.Embed(
                    title="Download",
                    description="Klicke auf den Button, um den Link des Bildes zu erhalten",
                    color=discord.Color.gold()
                )
                
                await message.channel.send(embed=embed, view=view)


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
