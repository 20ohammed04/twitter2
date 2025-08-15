import json
import random
import asyncio
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import base64

from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from PIL import Image  # لتحويل PNG إلى JPG

# --- إعدادات ---
TWEETS_FILE = "tweets.json"
STORAGE = "storage_state.json"
DEBUG_DIR = Path("debug_outputs")
DEBUG_DIR.mkdir(exist_ok=True)
MAX_SCREENSHOTS = 20  # حد أقصى للقطات
HISTORY_FILE = "post_history.json"
MAX_POSTS_PER_24H = 20
# فواصل بين التغريدات (ثواني) — المتطلب: 30-180 دقيقة
MIN_INTERVAL_SECONDS = 30 * 60
MAX_INTERVAL_SECONDS = 3 * 60 * 60

# ملف حالة العداء المجدول (لـ GitHub Actions)
RUNNER_STATE_FILE = "runner_state.json"

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
# تدوير السجلات لسهولة تتبع المشاكل عبر عدة تشغيلات
try:
    log_file = Path("runner.log")
    rfh = RotatingFileHandler(log_file, maxBytes=512_000, backupCount=3, encoding="utf-8")
    rfh.setFormatter(logging.Formatter('[%(asctime)s] %(message)s'))
    logging.getLogger().addHandler(rfh)
except Exception:
    pass


# ---------------- Utilities: history ----------------
def _now_ts():
    return int(datetime.now().timestamp())


def load_history():
    p = Path(HISTORY_FILE)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(hist):
    try:
        Path(HISTORY_FILE).write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logging.exception("Failed saving history: %s", e)


def clean_history(hist):
    cutoff = _now_ts() - 24 * 3600
    filtered = [h for h in hist if h.get("timestamp", 0) >= cutoff]
    return filtered


def count_last_24h(hist):
    hist = clean_history(hist)
    return len(hist)


def add_history_entry(hist, text_hash):
    hist.append({"hash": text_hash, "timestamp": _now_ts()})
    hist = clean_history(hist)
    save_history(hist)
    return hist


def canonical_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------- Utilities: runner state (for CI single-run mode) ----------------
def load_state():
    p = Path(RUNNER_STATE_FILE)
    if not p.exists():
        return {"next_post_at": 0}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"next_post_at": 0}


def save_state(state: dict):
    try:
        Path(RUNNER_STATE_FILE).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logging.exception("Failed saving state: %s", e)


# ---------------- Utilities: tweets ----------------
def load_tweets():
    with open(TWEETS_FILE, "r", encoding="utf-8") as f:
        return [t for t in json.load(f) if t.get("enabled", True)]


def shuffle_paragraphs(text: str) -> str:
    paragraphs = [p for p in text.strip().split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        return text
    random.shuffle(paragraphs)
    return "\n\n".join(paragraphs)


def shuffle_hashtags(hashtags):
    if not hashtags:
        return ""
    if random.choice([True, False]):
        return " ".join(hashtags) + " "
    else:
        return " " + " ".join(hashtags)


# ---------------- Utilities: shuffle words but keep (...) as unit ----------------
PARENTHESES_PLACEHOLDER = "__PAREN_PH_%d__"


def shuffle_words_preserve_parentheses(text: str) -> str:
    """
    إذا كانت التغريدة فقرة واحدة -> نقوم بعشوائية الكلمات،
    مع مراعاة أن أي نص داخل قوسين (...) يبقى وحدة واحدة.
    إذا كانت هناك فقرات متعددة، نرتب الفقرات.
    """
    paragraphs = [p for p in text.strip().split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        random.shuffle(paragraphs)
        return "\n\n".join(paragraphs)

    paragraph = paragraphs[0] if paragraphs else text
    par_matches = re.findall(r'\([^)]*\)', paragraph)
    placeholders = {}
    tmp = paragraph
    for i, m in enumerate(par_matches):
        key = PARENTHESES_PLACEHOLDER % i
        placeholders[key] = m
        tmp = tmp.replace(m, f" {key} ")

    tokens = [t for t in tmp.split() if t.strip()]
    if len(tokens) <= 1:
        for k, v in placeholders.items():
            paragraph = paragraph.replace(k, v)
        return paragraph

    random.shuffle(tokens)
    rebuilt = " ".join(tokens)
    for k, v in placeholders.items():
        rebuilt = rebuilt.replace(k, v)

    return rebuilt


# ---------------- Utilities: debug saving ----------------
async def save_debug(page, name_prefix):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    jpg_path = DEBUG_DIR / f"{name_prefix}_{ts}.jpg"
    html_path = DEBUG_DIR / f"{name_prefix}_{ts}.html"
    try:
        temp_png = DEBUG_DIR / f"{name_prefix}_{ts}.png"
        await page.screenshot(path=str(temp_png), full_page=True)
        img = Image.open(temp_png)
        img.convert("RGB").save(jpg_path, "JPEG", quality=70)
        try:
            temp_png.unlink()
        except Exception:
            pass

        content = await page.content()
        html_path.write_text(content, encoding="utf-8")

        logging.info(f"Saved debug files: {jpg_path}, {html_path}")

        screenshots = sorted(DEBUG_DIR.glob("*.jpg"), key=os.path.getmtime)
        if len(screenshots) > MAX_SCREENSHOTS:
            for old_file in screenshots[:-MAX_SCREENSHOTS]:
                try:
                    old_file.unlink()
                except Exception:
                    pass

    except Exception as e:
        logging.exception("Failed to save debug files: %s", e)


# ---------------- try_set_text ----------------
async def try_set_text(page, selector, text):
    try:
        await page.wait_for_selector(selector, timeout=3000, state="visible")
    except PWTimeout:
        return False
    except Exception:
        pass

    try:
        tag = await page.eval_on_selector(selector, "el => el.tagName && el.tagName.toLowerCase()")
        if tag in ("input", "textarea"):
            try:
                await page.fill(selector, text)
                return True
            except Exception:
                pass
    except Exception:
        pass

    script = """
    (sel, txt) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      try {
        el.focus();
        if (el.isContentEditable) {
          el.innerText = txt;
          el.dispatchEvent(new InputEvent('input', {bubbles:true}));
          el.dispatchEvent(new Event('change', {bubbles:true}));
          return true;
        }
        const tag = el.tagName.toLowerCase();
        if (tag === 'textarea' || tag === 'input') {
          el.value = txt;
          el.dispatchEvent(new Event('input', {bubbles:true}));
          el.dispatchEvent(new Event('change', {bubbles:true}));
          return true;
        }
        el.textContent = txt;
        el.dispatchEvent(new Event('input', {bubbles:true}));
        return true;
      } catch(e) {
        return false;
      }
    }
    """
    try:
        ok = await page.evaluate(script, selector, text)
        if ok:
            return True
    except Exception:
        pass

    try:
        await page.focus(selector)
        try:
            await page.keyboard.down("Control")
            await page.keyboard.press("a")
            await page.keyboard.up("Control")
            await page.keyboard.press("Backspace")
        except Exception:
            for _ in range(3):
                await page.keyboard.press("Backspace")
        await page.keyboard.type(text, delay=15)
        return True
    except Exception:
        return False


# ---------------- Core: post tweet (Control+Enter مباشرة) ----------------
async def post_tweet(page, content):
    logging.info("Navigating to compose page...")
    try:
        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(60000)
    except Exception:
        pass

    try:
        await page.goto("https://twitter.com/compose/tweet", timeout=60000)
    except Exception as e:
        logging.warning("page.goto warning/timeout: %s", e)

    try:
        await page.wait_for_selector("div[role='textbox'], textarea, div[aria-label='Tweet text']", timeout=45000)
    except Exception:
        await save_debug(page, "load_timeout")
        url = page.url
        logging.error("Timeout waiting for compose textbox. Current URL: %s", url)
        if any(p in url for p in ("login", "challenge", "account", "verify_password")):
            raise RuntimeError("الصفحة تطلب تسجيل دخول أو تحقق — من المحتمل أن session غير صالح. شغّل login_helper.py وأعد حفظ storage_state.json ثم جرّب مرة أخرى.")
        else:
            raise RuntimeError("تعذر تحميل صفحة التأليف أو إيجاد صندوق النص — راجع ملفات debug.")

    text_selectors = [
        "div[aria-label='Tweet text']",
        "div[role='textbox'][data-testid^='tweetTextarea']",
        "div[role='textbox']",
        "textarea",
        "div[data-testid='tweetTextarea_0']",
        "div[aria-label='Create a new Tweet']",
    ]

    filled = False
    used_sel = None
    for sel in text_selectors:
        logging.info(f"Trying text selector: {sel}")
        try:
            ok = await try_set_text(page, sel, content)
            if ok:
                logging.info(f"Filled text using: {sel}")
                filled = True
                used_sel = sel
                break
        except Exception as e:
            logging.warning("Error trying selector %s: %s", sel, e)

    if not filled:
        logging.error("Could not find/fill tweet textbox; saving debug files.")
        await save_debug(page, "no_textbox_after_load")
        raise RuntimeError("Tweet textbox not found or not fillable.")

    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    # Use Control+Enter مباشرة (ويندوز)
    try:
        if used_sel:
            try:
                await page.focus(used_sel)
            except Exception:
                pass
        await page.keyboard.press("Control+Enter")
        logging.info("Pressed Control+Enter to post tweet.")
    except Exception as e:
        logging.warning("Control+Enter failed: %s", e)
        # fallback to clicking buttons (كما في النسخة السابقة)
        tweet_button_selectors = [
            "div[data-testid='tweetButtonInline']",
            "div[data-testid='tweetButton']",
            "div[role='button'][data-testid*='tweet']",
            "div[aria-label='Tweet']",
            "div[role='button'][data-testid='toolBarTweetButton']",
            "button[data-testid='tweetButtonInline']",
            "button[aria-label='Tweet']",
            "button[data-testid='tweetButton']"
        ]
        clicked = False
        for btn in tweet_button_selectors:
            logging.info(f"Fallback trying tweet button selector: {btn}")
            try:
                await page.wait_for_selector(btn, timeout=5000, state="visible")
                disabled = await page.get_attribute(btn, "disabled")
                if disabled:
                    await asyncio.sleep(2)
                    disabled = await page.get_attribute(btn, "disabled")
                if not disabled:
                    await page.click(btn, timeout=7000)
                    clicked = True
                    logging.info("Clicked tweet button (fallback).")
                    break
            except Exception:
                try:
                    await page.evaluate("(sel) => document.querySelector(sel)?.click()", btn)
                    clicked = True
                    break
                except Exception:
                    continue
        if not clicked:
            await save_debug(page, "no_tweet_button_after_fill_fallback")
            raise RuntimeError("تعذّر إرسال التغريدة عن طريق الاختصار أو النقر. راجع debug.")

    await asyncio.sleep(2)
    logging.info("Tweet posted (or click/shortcut attempted).")


# ---------------- Utility: generate intervals for N posts ----------------
def generate_intervals_for_posts(n_posts: int, total_seconds: int, min_interval: int):
    """
    نريد نشر n_posts تغريدة بدءًا الآن، بحيث تنشر كلها خلال الـ total_seconds القادمة،
    مع جعل كل فاصل >= min_interval. طريقة: إذا n_posts == 1 => ننشر مرة واحدة فوراً (لا انتظار).
    خلاف ذلك: نولد (n_posts - 1) فواصل بين التغريدات (بعد أول نشر) بحيث تكون مجموعها = total_seconds.
    نستخدم عينة عشوائية (مثل Dirichlet) ثم نضيف الحد الأدنى لكل فاصل.
    """
    if n_posts <= 1:
        return []  # لا فواصل
    segments = n_posts - 1  # عدد الفواصل بين المنشورات (بعد أول منشور)
    min_total = segments * min_interval
    if min_total > total_seconds:
        # إذا لم تكن القيم معقولة، نخفض min_interval تلقائيًا
        min_interval = max(1, total_seconds // max(1, segments) // 2)
        min_total = segments * min_interval

    remaining = total_seconds - min_total
    # sample random positives
    xs = [random.random() for _ in range(segments)]
    s = sum(xs) or 1.0
    intervals = [min_interval + (remaining * (x / s)) for x in xs]
    # نحتفظ بالقيم كأعداد صحيحة (ثواني)
    intervals = [int(round(i)) for i in intervals]
    # قد نحتاج لتعديل صغير كي يكون مجموع الفواصل يساوي total_seconds (أو قريبًا بما فيه الكفاية)
    diff = total_seconds - sum(intervals)
    idx = 0
    while diff != 0:
        if diff > 0:
            intervals[idx % len(intervals)] += 1
            diff -= 1
        else:
            if intervals[idx % len(intervals)] > 1:
                intervals[idx % len(intervals)] -= 1
                diff += 1
        idx += 1
    return intervals


async def post_with_retries(page, content, retries=3, delay=10):
    """محاولة نشر التغريدة مع إعادة المحاولة عند الفشل."""
    for i in range(retries):
        try:
            await post_tweet(page, content)
            logging.info("Tweet successfully posted.")
            return True
        except Exception as e:
            logging.error(f"Attempt {i + 1}/{retries} to post failed: {e}")
            if i < retries - 1:
                logging.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                # قد تحتاج الصفحة لتحديث أو إعادة توجيه قبل المحاولة التالية
                try:
                    await page.reload(wait_until="domcontentloaded")
                    logging.info("Page reloaded before next attempt.")
                except Exception as reload_e:
                    logging.warning(f"Failed to reload page: {reload_e}")
            else:
                logging.error("All posting retries failed.")
                await save_debug(page, "post_failed_after_retries")
    return False


# ---------------- Main flow ----------------
async def main():
    if not Path(TWEETS_FILE).exists():
        raise FileNotFoundError(f"{TWEETS_FILE} not found in working directory.")
    tweets = load_tweets()
    if not tweets:
        logging.info("No enabled tweets found in tweets.json")
        return
    random.shuffle(tweets)

    # في CI: يمكن تمرير حالة الجلسة كـ base64 عبر متغير سري STORAGE_STATE_B64
    b64 = os.getenv("STORAGE_STATE_B64")
    if b64:
        try:
            Path(STORAGE).write_bytes(base64.b64decode(b64))
            logging.info("Decoded STORAGE_STATE_B64 into storage_state.json")
        except Exception as e:
            logging.exception("Failed to decode STORAGE_STATE_B64: %s", e)

    if not Path(STORAGE).exists():
        raise FileNotFoundError(f"{STORAGE} not found. Run 'python login_helper.py' to log in and create it, or provide STORAGE_STATE_B64.")

    # load & clean history
    history = clean_history(load_history())
    save_history(history)

    already = count_last_24h(history)
    logging.info(f"Already posted {already} times in the last 24 hours (limit {MAX_POSTS_PER_24H}).")
    remaining_to_post = MAX_POSTS_PER_24H - already
    if remaining_to_post <= 0:
        logging.info("No remaining posts required in this 24h window. Exiting.")
        return

    # وضع التشغيل: افتراضيًا "تشغيل مفرد لكل استدعاء" مناسب لـ GitHub Actions.
    # لتشغيل محلي متواصل، عيّن LOCAL_CONTINUOUS=1 في البيئة.
    local_continuous = os.getenv("LOCAL_CONTINUOUS") not in (None, "", "0", "false", "False")

    headless = True if os.getenv("CI") else False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context_kwargs = {"storage_state": STORAGE}
        context = await browser.new_context(**context_kwargs)

        try:
            context.set_default_timeout(60000)
            context.set_default_navigation_timeout(60000)
        except Exception:
            pass

        page = await context.new_page()

        if local_continuous:
            # النمط السابق: انشر عدة مرات حتى نصل للحد (مع فواصل مضمونة ضمن 30-180 دقيقة)
            # سنُنشئ فواصل عشوائية ضمن [MIN, MAX] دون تجاوز حد 24 ساعة.
            posts_left = remaining_to_post
            i = 0
            while posts_left > 0:
                # تحديث history والتأكد من السقف
                history = clean_history(load_history())
                if count_last_24h(history) >= MAX_POSTS_PER_24H:
                    break

                recent_hashes = {h["hash"] for h in history}
                candidates = [t for t in tweets if canonical_hash(t.get("text", "")) not in recent_hashes]
                if candidates:
                    chosen = random.choice(candidates)
                    modified_text = shuffle_paragraphs(chosen.get("text", ""))
                    logging.info("Selected a tweet not posted in last 24h.")
                else:
                    chosen = random.choice(tweets)
                    modified_text = shuffle_words_preserve_parentheses(chosen.get("text", ""))
                    logging.info("No new tweet available — repeating an old one with shuffled words (parentheses preserved).")

                hashtags_str = shuffle_hashtags(chosen.get("hashtags", []))
                if hashtags_str.strip() and hashtags_str.strip() in modified_text:
                    final_text = modified_text
                else:
                    final_text = (modified_text + hashtags_str) if hashtags_str.startswith(" ") else (hashtags_str + modified_text)

                print(f"[{datetime.now()}] Posting tweet: {final_text}")
                ok = await post_with_retries(page, final_text)
                if ok:
                    history = add_history_entry(history, canonical_hash(chosen.get("text", "")))
                    posts_left -= 1
                    i += 1

                if posts_left > 0:
                    wait_sec = random.randint(MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS)
                    logging.info(f"Waiting {wait_sec} seconds until next post (local continuous mode)...")
                    await asyncio.sleep(wait_sec)

        else:
            # النمط الافتراضي: نشر تغريدة واحدة فقط لكل تشغيل (للاستخدام في GitHub Actions)
            state = load_state()
            now = _now_ts()
            if state.get("next_post_at", 0) > now:
                logging.info(f"Not time yet. Next post at ts={state['next_post_at']}, now={now}.")
                await context.close()
                await browser.close()
                return

            # تحقق من السقف مرة أخرى
            history = clean_history(load_history())
            if count_last_24h(history) >= MAX_POSTS_PER_24H:
                logging.info("24h posting cap reached. Exiting.")
                await context.close()
                await browser.close()
                return

            recent_hashes = {h["hash"] for h in history}
            candidates = [t for t in tweets if canonical_hash(t.get("text", "")) not in recent_hashes]
            if candidates:
                chosen = random.choice(candidates)
                modified_text = shuffle_paragraphs(chosen.get("text", ""))
                logging.info("Selected a tweet not posted in last 24h.")
            else:
                chosen = random.choice(tweets)
                modified_text = shuffle_words_preserve_parentheses(chosen.get("text", ""))
                logging.info("No new tweet available — repeating an old one with shuffled words (parentheses preserved).")

            hashtags_str = shuffle_hashtags(chosen.get("hashtags", []))
            if hashtags_str.strip() and hashtags_str.strip() in modified_text:
                final_text = modified_text
            else:
                final_text = (modified_text + hashtags_str) if hashtags_str.startswith(" ") else (hashtags_str + modified_text)

            print(f"[{datetime.now()}] Posting single tweet (CI mode): {final_text}")
            ok = await post_with_retries(page, final_text)
            if ok:
                add_history_entry(history, canonical_hash(chosen.get("text", "")))
                # جدولة التالي ضمن [30, 180] دقيقة
                state["next_post_at"] = _now_ts() + random.randint(MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS)
                save_state(state)

        # إغلاق السياق والمتصفح بأمان
        try:
            await context.close()
        except Exception:
            pass
        try:
            await browser.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
