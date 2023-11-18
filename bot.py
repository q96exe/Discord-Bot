import discord
from discord.commands import Option
from PIL import Image
import requests
import io
import datetime
import asyncio
import aiosqlite
import json

intents = discord.Intents.all()
intents.members = True
bot = discord.Bot(intents=intents, members=True, messages=True)

DB = "user.db"
file_add_start = "021023"

@bot.event
async def on_ready():
    print(f"{bot.user} ist online")
    global admin_log_channel
    admin_log_channel = discord.utils.get(bot.get_all_channels(), name="・admin-logs・")

    async with aiosqlite.connect("user.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY,
            channel_id INTEGER 
            )
            """
        )
        await db.commit()

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, name="deinen Nachrichten"
        )
    )


async def create_user(user_id, channel_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO user (user_id, channel_id)
            VALUES (?, ?)
            """,
            (user_id, channel_id),
        )
        await db.commit()


@bot.slash_command(name="removeuser", description="Entfernt einen User aus der Datenbank")
async def remove_user_from_db(ctx, user: Option(discord.Member, required=True)):
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Fehler",
            description="Du hast keine Berechtigung diesen Command auszuführen!",
            color=discord.Color.red(),
        )
        await ctx.respond(embed=embed)
        return

    channel = bot.get_channel(int(await get_channel_from_id(user.id)))
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """
            DELETE FROM user WHERE user_id = ?
            """,
            (user.id,),
        )
        await db.commit()
        await channel.delete()

        embed = discord.Embed(
            title="Erfolgreich!",
            description=f"Der User {user.name} wurde erfolgreich aus der Datenbank entfernt und der Channel gelöscht!",
            color=discord.Color.brand_green(),
        )

        await ctx.respond(embed=embed, ephemeral=True, delete_after=8)


async def check_user_exists(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT * FROM user WHERE user_id = ?
            """,
            (user_id,),
        )
        result = await cursor.fetchall()
        return bool(result)


async def get_channel_from_id(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT channel_id FROM user WHERE user_id = ?
            """,
            (user_id,),
        )
        result = await cursor.fetchone()
        channel_id = result[0]
        return channel_id


async def get_user_from_channel(channel):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            """
            SELECT user_id FROM user WHERE channel_id = ?
            """,
            (channel.id,),
        )
        result = await cursor.fetchone()
        user_id = result[0]
        username = await discord.fetch_user(user_id)
        return username


async def resize_image_for_bleeter(attachments, channel):
    for attachment in attachments:
        url = attachment.url
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
        aspect_ratio = image.width / image.height

        # Check, if image is already in the right size
        # If not, resize it
        if image.width >= 650:
            new_width = int(650 * aspect_ratio)
            resized_image = image.resize((new_width, 650))
        else:
            resized_image = image

        print(len(resized_image.tobytes()))

        if len(resized_image.tobytes()) <= 1000000:
            output_buffer = await compress_image(resized_image)
        file = discord.File(
            output_buffer, filename=file_add_start + attachment.filename
        )

        embed = discord.Embed(
            title="Bild erfolgreich angepasst!",
            description="Klicke auf den Button, um den Link des Bildes zu erhalten",
            color=discord.Color.gold(),
        )

        attachment_message = await channel.send(file=file)

        attachment_url = attachment_message.attachments[0].url
        button = discord.ui.Button(
            label="Link", style=discord.ButtonStyle.primary, url=attachment_url
        )
        view = discord.ui.View()
        view.add_item(button)

        await channel.send(embed=embed, view=view)


async def compress_image(images, quality=100):
    output_buffer = io.BytesIO()
    image = images.convert("RGB")
    original_size = len(image.tobytes())
    if not original_size <= 1000000:
        while original_size >= 1000000:
            image.save(output_buffer, format="JPEG", optimize=True, quality=quality)
            output_size = len(output_buffer.getbuffer())
            if output_size <= 1000000:
                break
            quality = int(quality * 0.9)
            output_buffer.seek(0)
            output_buffer.truncate(0)
            image.save(output_buffer, format="JPEG", optimize=True, quality=quality)
        output_buffer.seek(0)
        print(len(output_buffer.getbuffer()))
        return output_buffer
    else:
        image.save(output_buffer, format="JPEG", optimize=False, quality=quality)
        output_buffer.seek(0)
        return output_buffer


async def compress_image_to_channel(attachments, channel):
    try:
        for attachment in attachments:
            url = attachment.url
            response = requests.get(url)
            image = Image.open(io.BytesIO(response.content))

            output_buffer = await compress_image(image)
            file = discord.File(
                output_buffer, filename=file_add_start + attachment.filename
            )

            embed = discord.Embed(
                title="Bild erfolgreich angepasst!",
                description="Klicke auf den Button, um den Link des Bildes zu erhalten",
                color=discord.Color.gold(),
            )

            attachment_message = await channel.send(file=file)

            attachment_url = attachment_message.attachments[0].url
            button = discord.ui.Button(
                label="Link", style=discord.ButtonStyle.primary, url=attachment_url
            )
            view = discord.ui.View()
            view.add_item(button)

            await channel.send(embed=embed, view=view)
    except Exception as e:
        embed_log = discord.Embed(
            title="Fehler",
            description=f"Es ist ein Fehler im Channel von {get_user_from_channel} aufgetreten:\n\n {e}",
            color=discord.Color.red(),
        )

        embed = discord.Embed(
            title="Fehler",
            description=f"Es ist ein Fehler aufgetreten! {channel.guild.owner.mention}",
            color=discord.Color.red(),
        )

        await log_channel.send(embed=embed_log)
        await channel.send(embed=embed)


@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="User")
    await member.add_roles(role)
    if await check_user_exists(member.id):
        existing_channel = bot.get_channel(int(await get_channel_from_id(member.id)))
        if existing_channel:
            category_prefix = "Channel"
            max_channels_per_category = 50

            category_name = None
            for category in member.guild.categories:
                if category.name.startswith(category_prefix):
                    category_num = category.name[len(category_prefix) :]
                    try:
                        category_num = int(category_num)
                    except ValueError:
                        continue
                    if len(category.channels) < max_channels_per_category:
                        category_name = category.name
                        break

            if category_name is None:
                category_num = 1
                while True:
                    category_name = category_prefix + str(category_num)
                    if discord.utils.get(member.guild.categories, name=category_name) is None:
                        break
                    category_num += 1

                category_list = []
                for category in member.guild.categories:
                    if category.name.startswith(category_prefix):
                        category_list.append(category)
                category_list.sort(key=lambda x: x.id)
                last_category = category_list[-1] if category_list else None
                new_position = last_category.position + 1 if last_category else 0
                category = await member.guild.create_category(
                    category_name, position=new_position
                )
            await existing_channel.edit(
                category=discord.utils.get(member.guild.categories, name=category_name)
            )
            await existing_channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True,
                reason="User joined again, Text Channel moved",
            )
            await existing_channel.set_permissions(
                member.guild.default_role,
                read_messages=False,
                send_messages=False,
                reason="User joined again, Text Channel moved",
            )
            global log_channel
            log_channel = discord.utils.get(member.guild.channels, name="・logs・")

            embed = discord.Embed(
                title=f"Textkanal von {member.name} wurde bereits erstellt",
                description=f"Die Berechtigungen wurden erneut vergeben",
                color=discord.Color.gold(),
            )
            await log_channel.send(embed=embed)
            return
    else:
        category_prefix = "Channel"
        max_channels_per_category = 50

        category_name = None
        for category in member.guild.categories:
            if category.name.startswith(category_prefix):
                category_num = category.name[len(category_prefix) :]
                try:
                    category_num = int(category_num)
                except ValueError:
                    continue
                if len(category.channels) < max_channels_per_category:
                    category_name = category.name
                    break

        if category_name is None:
            category_num = 1
            while True:
                category_name = category_prefix + str(category_num)
                if (
                    discord.utils.get(member.guild.categories, name=category_name)
                    is None
                ):
                    break
                category_num += 1

            category_list = []
            for category in member.guild.categories:
                if category.name.startswith(category_prefix):
                    category_list.append(category)
            category_list.sort(key=lambda x: x.id)
            last_category = category_list[-1] if category_list else None
            new_position = last_category.position + 1 if last_category else 0
            category = await member.guild.create_category(
                category_name, position=new_position
            )

        channel = await member.guild.create_text_channel(
            str(member.name), category=category
        )
        await channel.set_permissions(
            member,
            read_messages=True,
            send_messages=True,
            reason="User joined, Text Channel created",
        )
        await channel.set_permissions(
            member.guild.default_role,
            read_messages=False,
            send_messages=False,
            reason="User joined, Text Channel created",
        )

        await create_user(member.id, channel.id)

        embed = discord.Embed(
            title=f"Textkanal von {member.name} wurde erfolgreich erstellt",
            description=f"Der Textkanal von {member.name} wurde erfolgreich erstellt",
            color=discord.Color.gold(),
        )

        channel_embed = discord.Embed(
            title=f"Willkommen {member.name}!",
            description=f"Dein eigener Textkanal wurde erfolgreich erstellt. Hier kannst du Bilder hochladen. \n\n\
                Sobald du ein Bild hochgeladen hast, wird dir ein Button angezeigt, mit dem du den korrekten Link des Bildes erhalten kannst. \n\n\
                Außerdem kannst du das Bild direkt auf die passende Größe und Qualität für Bleeter anpassen. \n\n\
                Weitere Hilfe bekommst du mit dem Befehl /help. \n\n\
                Wenn Fehler auftreten, kannst du diese gern bei {member.guild.owner.mention} melden.",
            color=discord.Color.gold(),
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
            max_channels_per_category = 50
            category_prefix = "Channel - User left"
            category_list = []

            for category in member.guild.categories:
                if category.name.startswith(category_prefix):
                    category_list.append(category)

            category_list.sort(key=lambda x: x.id)

            if len(category_list[0].channels) >= max_channels_per_category:
                category_num = (
                    int(category_list[-1].name.split()[-1]) + 1 if category_list else 1
                )
                category_name = f"{category_prefix} {category_num}"
                category_position = (
                    category_list[-1].position + 1 if category_list else 0
                )
                category = await member.guild.create_category(
                    category_name, position=category_position
                )
            else:
                category = category_list[0]

            await existing_channel.edit(category=category)
            log_channel = discord.utils.get(member.guild.channels, name="・logs・")

            embed = discord.Embed(
                title=f"Textkanal von {member.name} wurde erfolgreich verschoben",
                description=f"Der Textkanal von {member.name} wurde erfolgreich verschoben, da er den Server verlassen hat",
                color=discord.Color.gold(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_channel.send(embed=embed)


@bot.event
async def on_message(message):
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.startswith(file_add_start):
                return
            if (
                attachment.filename.endswith(".png")
                or attachment.filename.endswith(".PNG")
                or attachment.filename.endswith(".jpg")
                or attachment.filename.endswith(".JPG")
                or attachment.filename.endswith(".jpeg")
                or attachment.filename.endswith(".JPEG")
                or attachment.filename.endswith(".gif")
                or attachment.filename.endswith(".GIF")
            ):
                link = attachment.url
                if ".png" in link:
                    index = link.index(".png")
                    new_link = link[: index + len(".png")]
                elif ".PNG" in link:
                    index = link.index(".PNG")
                    new_link = link[: index + len(".PNG")]
                elif ".jpg" in link:
                    index = link.index(".jpg")
                    new_link = link[: index + len(".jpg")]
                elif ".JPG" in link:
                    index = link.index(".JPG")
                    new_link = link[: index + len(".JPG")]
                elif ".jpeg" in link:
                    index = link.index(".jpeg")
                    new_link = link[: index + len(".jpeg")]
                elif ".JPEG" in link:
                    index = link.index(".JPEG")
                    new_link = link[: index + len(".JPEG")]
                elif ".gif" in link:
                    index = link.index(".gif")
                    new_link = link[: index + len(".gif")]
                elif ".GIF" in link:
                    index = link.index(".GIF")
                    new_link = link[: index + len(".GIF")]

                global view
                view = discord.ui.View()

                button = discord.ui.Button(
                    label="Link", style=discord.ButtonStyle.primary, url=new_link
                )
                bleeter_button = discord.ui.Button(
                    label="Auf Bleetergröße anpassen", style=discord.ButtonStyle.primary
                )
                bleeter_button.callback = lambda _: asyncio.create_task(
                    resize_image_for_bleeter(message.attachments, message.channel)
                )
                compress_image_button = discord.ui.Button(
                    label="Komprimieren", style=discord.ButtonStyle.success
                )
                compress_image_button.callback = lambda _: asyncio.create_task(
                    compress_image_to_channel(message.attachments, message.channel)
                )
                view.add_item(button)
                view.add_item(bleeter_button)
                view.add_item(compress_image_button)

                embed = discord.Embed(
                    title="Download",
                    description=f"Klicke auf den Button, um den Link des Bildes zu erhalten\n\nWillst du, dass das Bild auf die passende Größe für Bleeter angepasst wird? Dann klicke auf den Button 'Auf Bleetergröße anpassen'. \n\nWillst du das Bild nur komprimieren? Dann klicke auf 'Komprimieren'.",
                    color=discord.Color.brand_green(),
                )

                await message.channel.send(
                    embed=embed, view=view, reference=message, mention_author=True
                )

                adminEmbed = discord.Embed(
                    title="Log",
                    description=f"{message.author.name} hat ein Bild hochgeladen: {attachment.filename}",
                    color=discord.Color.brand_green(),
                )

                adminEmbed.set_thumbnail(url=message.author.display_avatar.url)
                await admin_log_channel.send(embed=adminEmbed)

            else:
                error_embed = discord.Embed(
                    title="FEHLER",
                    description="Es ist ein Fehler aufgetreten! Als Dateiendungen sind nur .png, .jpg, .jpeg und .gif erlaubt.",
                    color=discord.Color.brand_red(),
                )

                await message.channel.send(
                    embed=error_embed, reference=message, mention_author=True
                )

                adminEmbed = discord.Embed(
                    title="Log",
                    description=f"{message.author.name} hat eine ungültige Datei hochgeladen: {attachment.filename}",
                    color=discord.Color.brand_red(),
                )

                adminEmbed.set_thumbnail(url=message.author.display_avatar.url)
                await admin_log_channel.send(embed=adminEmbed)


@bot.slash_command(description="Berechne das Enddatum und die Endzeit")
async def time(
    ctx, start_date: Option(), start_time: Option(), hours: Option(), minutes: Option()
):
    try:
        start_date = datetime.datetime.strptime(start_date, "%d.%m.%Y")
        start_time = datetime.datetime.strptime(start_time, "%H:%M")
        start_datetime = datetime.datetime.combine(start_date.date(), start_time.time())
        end_datetime = start_datetime + datetime.timedelta(
            hours=int(hours), minutes=int(minutes)
        )
        embed = discord.Embed(
            title="Enddatum und Endzeit",
            description=f"Das Enddatum ist der {end_datetime.strftime('%d.%m.%Y')} um {end_datetime.strftime('%H:%M')} Uhr",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Startdatum: ", value=start_date.strftime("%d.%m.%Y"), inline=False
        )
        embed.add_field(
            name="Startzeit: ", value=start_time.strftime("%H.%M"), inline=False
        )
        embed.add_field(name="Stunden: ", value=hours, inline=False)
        embed.add_field(name="Minuten: ", value=minutes, inline=False)

        await ctx.respond(embed=embed)
    except ValueError:
        embed = discord.Embed(
            title="Fehler",
            description="Es wurde kein gültiges Startdatum und/oder Startzeit angegeben. \n\nBitte gib das Startdatum und die Startzeit im Format `dd.mm.yyyy` und `hh:mm` an. \n\nBeispiel: \n\n`/time 01.01.2023 12:00 1 30`",
            color=discord.Color.red(),
        )
        await ctx.respond(embed=embed)


@bot.slash_command(description="Zeigt die Hilfe an")
async def help(ctx):
    embed = discord.Embed(
        title="Hilfe",
        description="Hier findest du alle Befehle, die du verwenden kannst:",
        color=discord.Color.gold(),
    )
    embed.add_field(name="/help", value="Zeigt die Hilfe an", inline=False)
    embed.add_field(
        name="/time", value="Berechnet das Enddatum und die Endzeit", inline=False
    )
    embed.add_field(
        name="Bildoptionen?",
        value="Lade einfach ein Bild hoch und klick auf die Buttons!",
        inline=False,
    )
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(description="Sendet ein Embed in einen bestimmten Channel")
async def say(ctx, target_channel: Option(discord.TextChannel, required=True), titel: Option(str, required=True), text: Option(str, required=True)):
    if not ctx.author.guild_permissions.administrator:
        error_embed = discord.Embed(
            title="Fehler",
            description="Du hast keine Berechtigung diesen Command auszuführen!",
            color=discord.Color.red(),
        )
        await ctx.respond(embed=error_embed)
    else:
        embed = discord.Embed(
            title=titel,
            color=discord.Color.gold(),
            description=text,
        )

        await target_channel.send(embed=embed)
        await ctx.respond(f"Nachricht erfolgreich gesendet in den Channel {target_channel} gesendet!", ephemeral=True, delete_after=8)

@bot.slash_command(description="Erstelle den Channel eines Users")
async def create_channel(ctx, member: Option(discord.Member, required=True)):
    if not ctx.author.guild_permissions.administrator:
        error_embed = discord.Embed(
            title="Fehler",
            description="Du hast keine Berechtigung diesen Command auszuführen!",
            color=discord.Color.red(),
        )
        await ctx.respond(embed=error_embed)
    else:
        role = discord.utils.get(member.guild.roles, name="User")
        await member.add_roles(role)
        if await check_user_exists(member.id):
            existing_channel = bot.get_channel(int(await get_channel_from_id(member.id)))
            if existing_channel:
                category_prefix = "Channel"
                max_channels_per_category = 50

                category_name = None
                for category in member.guild.categories:
                    if category.name.startswith(category_prefix):
                        category_num = category.name[len(category_prefix) :]
                        try:
                            category_num = int(category_num)
                        except ValueError:
                            continue
                        if len(category.channels) < max_channels_per_category:
                            category_name = category.name
                            break

                if category_name is None:
                    category_num = 1
                    while True:
                        category_name = category_prefix + str(category_num)
                        if discord.utils.get(member.guild.categories, name=category_name) is None:
                            break
                        category_num += 1

                    category_list = []
                    for category in member.guild.categories:
                        if category.name.startswith(category_prefix):
                            category_list.append(category)
                    category_list.sort(key=lambda x: x.id)
                    last_category = category_list[-1] if category_list else None
                    new_position = last_category.position + 1 if last_category else 0
                    category = await member.guild.create_category(
                        category_name, position=new_position
                    )
                await existing_channel.edit(
                    category=discord.utils.get(member.guild.categories, name=category_name)
                )
                await existing_channel.set_permissions(
                    member,
                    read_messages=True,
                    send_messages=True,
                    reason="User joined again, Text Channel moved",
                )
                await existing_channel.set_permissions(
                    member.guild.default_role,
                    read_messages=False,
                    send_messages=False,
                    reason="User joined again, Text Channel moved",
                )
                global log_channel
                log_channel = discord.utils.get(member.guild.channels, name="・logs・")

                embed = discord.Embed(
                    title=f"Textkanal von {member.name} wurde bereits erstellt",
                    description=f"Die Berechtigungen wurden erneut vergeben",
                    color=discord.Color.gold(),
                )
                await log_channel.send(embed=embed)
                return
        else:
            category_prefix = "Channel"
            max_channels_per_category = 50

            category_name = None
            for category in member.guild.categories:
                if category.name.startswith(category_prefix):
                    category_num = category.name[len(category_prefix) :]
                    try:
                        category_num = int(category_num)
                    except ValueError:
                        continue
                    if len(category.channels) < max_channels_per_category:
                        category_name = category.name
                        break

            if category_name is None:
                category_num = 1
                while True:
                    category_name = category_prefix + str(category_num)
                    if (
                        discord.utils.get(member.guild.categories, name=category_name)
                        is None
                    ):
                        break
                    category_num += 1

                category_list = []
                for category in member.guild.categories:
                    if category.name.startswith(category_prefix):
                        category_list.append(category)
                category_list.sort(key=lambda x: x.id)
                last_category = category_list[-1] if category_list else None
                new_position = last_category.position + 1 if last_category else 0
                category = await member.guild.create_category(
                    category_name, position=new_position
                )

            channel = await member.guild.create_text_channel(
                str(member.name), category=category
            )
            await channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True,
                reason="User joined, Text Channel created",
            )
            await channel.set_permissions(
                member.guild.default_role,
                read_messages=False,
                send_messages=False,
                reason="User joined, Text Channel created",
            )

            await create_user(member.id, channel.id)

            embed = discord.Embed(
                title=f"Textkanal von {member.name} wurde erfolgreich erstellt",
                description=f"Der Textkanal von {member.name} wurde erfolgreich erstellt",
                color=discord.Color.gold(),
            )

            channel_embed = discord.Embed(
                title=f"Willkommen {member.name}!",
                description=f"Dein eigener Textkanal wurde erfolgreich erstellt. Hier kannst du Bilder hochladen. \n\n\
                    Sobald du ein Bild hochgeladen hast, wird dir ein Button angezeigt, mit dem du den korrekten Link des Bildes erhalten kannst. \n\n\
                    Außerdem kannst du das Bild direkt auf die passende Größe und Qualität für Bleeter anpassen. \n\n\
                    Weitere Hilfe bekommst du mit dem Befehl /help. \n\n\
                    Wenn Fehler auftreten, kannst du diese gern bei {member.guild.owner.mention} melden.",
                color=discord.Color.gold(),
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            channel_embed.set_thumbnail(url=member.display_avatar.url)
            textchannel = discord.utils.get(member.guild.channels, name="・logs・")
            await textchannel.send(embed=embed)
            await channel.send(embed=channel_embed)
            await ctx.respond(embed=embed, ephemeral=True, delete_after=8)

def getToken():
    with open("token.json", "r") as f:
        token = json.load(f)
        return token["token"]

bot.run(getToken())