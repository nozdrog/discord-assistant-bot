import discord
from discord.ext import commands
import openai
import asyncio
import os
import aiohttp

openai.api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")
discord_token = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def download_discord_file(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(filename, 'wb') as f:
                    f.write(await resp.read())
                return filename
            else:
                return None

def upload_file_to_openai(filepath):
    with open(filepath, "rb") as f:
        file = openai.files.create(file=f, purpose="assistants")
        return file.id

async def handle_excel_file(attachment, message, thread_id):
    filename = attachment.filename
    await message.channel.send(f"📥 Downloading `{filename}`...")

    # Download from Discord
    file_path = await download_discord_file(attachment.url, filename)
    if not file_path:
        await message.channel.send("❌ Failed to download the file.")
        return

    # Upload to OpenAI
    try:
        file_id = upload_file_to_openai(file_path)
    except Exception as e:
        await message.channel.send(f"❌ Failed to upload to OpenAI: {str(e)}")
        return

    # Send to Assistant
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=(
            "This file contains an Excel dataset. "
            "Please filter the column 'opportunity_lead_handler(zakaznik)' to only include rows with 'Everest'. "
            "Then remove duplicate values in the 'ERP ID(Zakaznik)' column. "
            "Finally, count the number of dates in the column 'Datum Prvniho Filingu(zakaznik)' "
            "that fall between 24.3.2025 and 30.3.2025. "
            "Return all results in a clear, human-readable format."
        ),
        file_ids=[file_id]
    )

    await message.channel.send("📊 File uploaded and sent to Assistant. Processing...")

    os.remove(file_path)  # optional: clean up

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Handle Excel file uploads
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(".xlsx"):
                await handle_excel_file(attachment, message, thread.id)
                return

    user_input = message.content

    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        await asyncio.sleep(1)

    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[0].content[0].text.value

    await message.channel.send(reply)

bot.run(discord_token)
