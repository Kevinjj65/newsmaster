import asyncio
import requests
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from transformers import pipeline

BOT_TOKEN = os.getenv("BOT_TOKEN")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Initialize summarizer
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey there! 👋 I'm your AI News Bot.\nType /latest to get summarized headlines."
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loop = asyncio.get_running_loop()

    # Run the blocking request in executor
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    data = await loop.run_in_executor(None, lambda: requests.get(url).json())

    if data.get("articles"):
        news_list = []
        for article in data["articles"][:3]:  # Top 3 to keep it quick
            text_to_summarize = article.get("description") or article.get(
                "content") or article["title"]
            if text_to_summarize:
                # Run summarizer in executor
                summary_result = await loop.run_in_executor(
                    None,
                    lambda: summarizer(
                        text_to_summarize, max_length=40, min_length=10, do_sample=False)
                )
                summary = summary_result[0]['summary_text']
                news_list.append(
                    f"📰 {article['title']}\n💡 Summary: {summary}\n🔗 {article['url']}"
                )

        await update.message.reply_text("\n\n".join(news_list))
    else:
        await update.message.reply_text("Sorry, couldn't fetch the news 😢")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    print("Bot is running...")
    app.run_polling()
