import discord
from discord.commands import Option
from PIL import Image
import requests
import io
import asyncio

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

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="deinen Nachrichten"))

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

@bot.slash_command(name="removeuser", description="Entfernt einen User aus der Datenbank")
async def remove_user_from_db(ctx, user: Option(discord.Member, required=True)):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """
            DELETE FROM user WHERE user_id = ?
            """,
            (user.id,)
        )
        await db.commit()
        await ctx.respond(f"Der User {user.name} wurde erfolgreich aus der Datenbank entfernt")

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
    
async def resize_image_for_bleeter(attachments, channel):
    for attachment in attachments:
        url = attachment.url
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
        aspect_ratio = image.width / image.height
        new_width = int(650 * aspect_ratio)
        resized_image = image.resize((new_width, 650))
        
        output_buffer = await compress_image(resized_image)
        
        file = discord.File(output_buffer, filename="170123" + attachment.filename)
        
        embed = discord.Embed(
            title="Bild erfolgreich angepasst",
            description="Klicke auf den Button, um den Link des Bildes zu erhalten",
            color=discord.Color.gold()
        )
    
        attachment_message = await channel.send(file=file)

        attachment_url = attachment_message.attachments[0].url
        button = discord.ui.Button(label="Link", style=discord.ButtonStyle.primary, url=attachment_url)
        view = discord.ui.View()
        view.add_item(button)

        await channel.send(embed=embed, view=view)


async def compress_image(image, quality=100):
    output_buffer = io.BytesIO()
    image = image.convert("RGB")
    image.save(output_buffer, format="JPEG", optimize=True, quality=quality)
    while output_buffer.tell() > 1000000:
        output_buffer.seek(0)
        new_quality = int(quality * 0.9)
        image.save(output_buffer, format="JPEG", optimize=True, quality=new_quality)
        quality = new_quality
        print(f"Image size: {output_buffer.tell()}")  # Überprüfen des Pufferinhalts
    output_buffer.seek(0)
    return output_buffer
        

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="User")
    await member.add_roles(role)
    if await check_user_exists(member.id):
        existing_channel = bot.get_channel(int(await get_channel_from_id(member.id)))
        if existing_channel:
            await existing_channel.edit(category=discord.utils.get(member.guild.categories, name="Channel"))
            await existing_channel.set_permissions(member, read_messages=True, send_messages=True, reason="User joined, Text Channel created")
            await existing_channel.set_permissions(member.guild.default_role, read_messages=False, send_messages=False, reason="User joined, Text Channel created")
            log_channel = discord.utils.get(member.guild.channels, name="・logs・")

            embed = discord.Embed(
                title=f"Textkanal von {member.name} wurde bereits erstellt",
                description=f"Die Berechtigungen wurden erneut vergeben",
                color=discord.Color.gold()
            )   
            await log_channel.send(embed=embed)
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
            description=f"Dein eigener Textkanal wurde erfolgreich erstellt. Hier kannst du Bilder für z.B. Akten hochladen. \n\n\
                Sobald du ein Bild hochgeladen hast, wird dir ein Button angezeigt, mit dem du den korrekten Link des Bildes für die Akten erhalten kannst. \n\n\
                Außerdem kannst du das Bild direkt auf die passende Größe und Qualität für Bleeter anpassen. \n\n\
                Wenn Fehler auftreten, kannst du diese gern bei {member.guild.owner.mention} melden.",
            color=discord.Color.gold()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        channel_embed.set_thumbnail(url=member.display_avatar.url)
        textchannel = discord.utils.get(member.guild.channels, name="・logs・")
        await textchannel.send(embed=embed)
        await channel.send(embed=channel_embed)


@bot.event
async def on_member_remove(member):
    if await check_user_exists(member.id):
        existing_channel = bot.get_channel(int(await get_channel_from_id(member.id)))
        if existing_channel:
            await existing_channel.edit(category=discord.utils.get(member.guild.categories, name="Channel - User left"))
            log_channel = discord.utils.get(member.guild.channels, name="・logs・")

            embed = discord.Embed(
                title=f"Textkanal von {member.name} wurde erfolgreich verschoben",
                description=f"Der Textkanal von {member.name} wurde erfolgreich verschoben, da er den Server verlassen hat",
                color=discord.Color.gold()
            )   
            await log_channel.send(embed=embed)


@bot.event
async def on_message(message):
    if message.attachments:
        for attachment in message.attachments:
            if(attachment.filename.startswith("170123")):
                return
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
                bleeter_button = discord.ui.Button(label="Auf Bleetergröße anpassen", style=discord.ButtonStyle.primary)
                bleeter_button.callback = lambda _: asyncio.create_task(resize_image_for_bleeter(message.attachments, message.channel))
                view = discord.ui.View()
                view.add_item(button)
                view.add_item(bleeter_button)

                embed = discord.Embed(
                    title="Download",
                    description="Klicke auf den Button, um den Link des Bildes zu erhalten",
                    color=discord.Color.brand_green()
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
