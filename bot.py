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
        await db.commit()

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

async def check_user_exists(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT * FROM user WHERE user_id = ?
            """,
            (user_id,)
        )
        result = await cursor.fetchall()
        return bool(result)
    
async def get_channel_from_id(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT channel_id FROM user WHERE user_id = ?
            """, 
            (user_id,)
        )
        result = await cursor.fetchone()
        channel_id = result[0]
        return channel_id
        
        
@bot.slash_command(description="DB Test", name="createdbuser")
async def create_db_user(ctx, user: Option(discord.Member, default=None)):
    await create_user(user.id, "1085244955657769071")

    embed = discord.Embed(
        title=f"User {user.name} wurde erfolgreich erstellt",
        description=f"User {user.name} wurde erfolgreich erstellt",
        color=discord.Color.gold()
    )

    await ctx.respond(embed=embed, ephemeral=True)

# TODO: Create a function to check if the user has a channel

@bot.event
async def on_member_join(member):
    if await check_user_exists(member.id):
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

    channel_embed = discord.Embed(
        title=f"Willkommen {member.name}!",
        description=f"Dein eigener Textkanal wurde erfolgreich erstellt. Hier kannst du Bilder für z.B. Akten hochladen. \n\nSobald du ein Bild hochgeladen hast, wird dir ein Button angezeigt, mit dem du den korrekten Link des Bildes für die Akten erhalten kannst. \n\nWenn Fehler auftreten, kannst du diese gern bei {member.guild.owner.mention} melden.",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    channel_embed.set_thumbnail(url=member.display_avatar.url)
    textchannel = discord.utils.get(member.guild.channels, name="・logs・")
    await textchannel.send(embed=embed)
    await channel.send(embed=channel_embed)


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
async def createchannel(ctx, member: Option(discord.Member, default=None)):
    if await check_user_exists(member.id):
        existing_channel = bot.get_channel(int(await get_channel_from_id(member.id)))
        if existing_channel:  
            await existing_channel.set_permissions(member, read_messages=True, send_messages=True, reason="User joined, Text Channel created")
            await existing_channel.set_permissions(member.guild.default_role, read_messages=False, send_messages=False, reason="User joined, Text Channel created")
            log_channel = discord.utils.get(member.guild.channels, name="・logs・")

            embed = discord.Embed(
                title=f"Textkanal von {member.name} wurde bereits erstellt",
                description=f"Die Berechtigungen wurden erneut vergeben",
                color=discord.Color.gold()
            )   
            await log_channel.send(embed=embed)
            await ctx.respond(embed=embed, ephemeral=True)
            return
    else:
        category = discord.utils.get(member.guild.categories, name="Channel")
        channel = await member.guild.create_text_channel(str(member.name), category=category)
        await channel.set_permissions(member, read_messages=True, send_messages=True, reason="User joined, Text Channel created")
        await channel.set_permissions(member.guild.default_role, read_messages=False, send_messages=False, reason="User joined, Text Channel created")
        
        await create_user(member.id, channel.id)

        embed = discord.Embed(
            title=f"Textkanal von {member.name} wurde erfolgreich erstellt",
            description=f"Der Textkanal von {member.name} wurde erfolgreich erstellt",
            color=discord.Color.gold()
        )

        channel_embed = discord.Embed(
            title=f"Willkommen {member.name}!",
            description=f"Dein eigener Textkanal wurde erfolgreich erstellt. Hier kannst du Bilder für z.B. Akten hochladen. \n\nSobald du ein Bild hochgeladen hast, wird dir ein Button angezeigt, mit dem du den korrekten Link des Bildes für die Akten erhalten kannst. \n\nWenn Fehler auftreten, kannst du diese gern bei {member.guild.owner.mention} melden.",
            color=discord.Color.gold()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        channel_embed.set_thumbnail(url=member.display_avatar.url)
        textchannel = discord.utils.get(member.guild.channels, name="・logs・")
        await textchannel.send(embed=embed)
        await channel.send(embed=channel_embed)

        await ctx.respond("Erstellt", ephemeral=True)


def getToken():
    with open('token.json', 'r') as f:
        token = json.load(f)
        return token['token']
    

bot.run(getToken())
