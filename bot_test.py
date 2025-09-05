import os
import requests
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import google.generativeai as genai
from typing import Union  # <<< --- ADD THIS IMPORT

# --- 1. CONFIGURATION and INITIALIZATION ---

# Load environment variables from a .env file
load_dotenv()

# Securely fetch your API keys
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEWSDATA_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# A critical check to ensure the bot doesn't start without its keys
if not BOT_TOKEN or not NEWSDATA_API_KEY or not GEMINI_API_KEY:
    raise ValueError(
        "Error: BOT_TOKEN, NEWS_API_KEY, and GEMINI_API_KEY must be set in your .env file."
    )

# Configure the Gemini API client
print("Configuring Google Gemini AI...")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
print("Gemini AI configured successfully.")


# --- 2. CORE FUNCTIONS (News Fetching & AI Summarization) ---

# vvv --- THIS IS THE LINE WE FIXED --- vvv
def fetch_news(topic: str) -> Union[dict, None]:
    """Fetches the top news article for a given topic from NewsData.io."""
    # The API URL, searching for the topic in English, within India.
    url = f"https://newsdata.io/api/1/news?apikey={NEWSDATA_API_KEY}&q={topic}&language=en&country=in"
    try:
        response = requests.get(url)
        # Raise an exception if the request was unsuccessful (e.g., 404, 500)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success" and data.get("results"):
            return data["results"][0]  # Return the first (top) article
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news from API: {e}")
    return None


async def summarize_with_gemini(article_content: str, topic: str) -> str:
    """Generates a summary of the article using the Gemini API."""
    if not article_content:
        return "The article content was empty, so I couldn't summarize it."

    # This is the "prompt" that instructs our AI agent
    prompt = f"""
    You are an expert news assistant for a Telegram bot based in Muvattupuzha, Kerala.
    A user wants to know about "{topic}".
    Based on the following news article, provide a clear, concise, and engaging summary in about 50-60 words.
    Start your summary with a single, relevant emoji.

    ARTICLE TEXT:
    ---
    {article_content}
    ---
    """
    try:
        # Asynchronously generate the content
        response = await gemini_model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return "Sorry, I had a problem summarizing the news with the AI."


# --- 3. TELEGRAM COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a friendly welcome message when the /start command is issued."""
    welcome_message = (
        "👋 Hello there! I am your AI-powered news bot.\n\n"
        "Just send me a topic using the /news command.\n\n"
        "For example: `/news ISRO` or `/news Indian Cricket`"
    )
    await update.message.reply_text(welcome_message)


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The main command to fetch and summarize news."""
    # Check if the user provided a topic
    if not context.args:
        await update.message.reply_text(
            "Please provide a topic after the command. \nExample: `/news Technology`"
        )
        return

    topic = " ".join(context.args)
    await update.message.reply_text(f"🤖 Searching for news about '{topic}' and summarizing with AI...")

    # Use a non-blocking call to fetch the news
    loop = asyncio.get_running_loop()
    article = await loop.run_in_executor(None, fetch_news, topic)

    if article:
        # Prioritize 'content' for the best summary, with fallbacks
        text_to_process = article.get(
            "content") or article.get("description") or ""

        # Get the AI-powered summary
        summary = await summarize_with_gemini(text_to_process, topic)

        # Prepare the final message
        title = article.get('title', 'No Title Available')
        article_url = article.get("link", "#")

        # Format the message using Markdown for a rich look
        message = f"📰 *{title}*\n\n{summary}\n\n🔗 [Read Full Article]({article_url})"
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"Sorry, I couldn't find any recent news articles about '{topic}'."
        )


# --- 4. MAIN APPLICATION SETUP ---

if __name__ == "__main__":
    print("Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register the command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", news))

    # Start the bot and wait for commands
    print("Bot is running and listening for commands...")
    app.run_polling()
