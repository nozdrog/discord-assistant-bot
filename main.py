import discord
from discord.ext import commands
import openai
import asyncio
import os

openai.api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")
discord_token = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
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