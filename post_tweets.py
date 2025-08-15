import json
import random
import asyncio
from playwright.async_api import async_playwright
import os
import time
from datetime import datetime

TWEETS_FILE = "tweets.json"

def load_tweets():
    with open(TWEETS_FILE, "r", encoding="utf-8") as f:
        return [t for t in json.load(f) if t.get("enabled", True)]

def shuffle_paragraphs(text):
    paragraphs = text.strip().split("\n\n")
    random.shuffle(paragraphs)
    return "\n\n".join(paragraphs)

def shuffle_hashtags(hashtags):
    if random.choice([True, False]):
        return " ".join(hashtags) + " "
    else:
        return " " + " ".join(hashtags)

async def post_tweet(page, content):
    await page.goto("https://twitter.com/compose/tweet")
    await page.wait_for_selector("div[aria-label='Tweet text']", timeout=10000)
    await page.fill("div[aria-label='Tweet text']", content)
    await page.click("div[data-testid='tweetButtonInline']")
    await asyncio.sleep(5)

async def main():
    tweets = load_tweets()
    random.shuffle(tweets)

    storage_state_path = "storage_state.json"
    with open(storage_state_path, "wb") as f:
        f.write(os.urandom(1))  # placeholder just to ensure file exists

    with open("storage_state.json", "wb") as f:
        pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="storage_state.json")
        page = await context.new_page()

        for tweet in tweets:
            modified_text = shuffle_paragraphs(tweet["text"])
            hashtags_str = shuffle_hashtags(tweet["hashtags"])
            if hashtags_str.strip() in modified_text:
                final_text = modified_text
            else:
                if hashtags_str.startswith(" "):
                    final_text = modified_text + hashtags_str
                else:
                    final_text = hashtags_str + modified_text

            print(f"[{datetime.now()}] Posting tweet: {final_text}")
            await post_tweet(page, final_text)
            await asyncio.sleep(random.randint(180, 240))  # wait 3-4 minutes

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

