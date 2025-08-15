#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple tweet manager for tweets.json

Usage examples:
  python manage_tweets.py --list
  python manage_tweets.py --add --text "نص التغريدة" --hashtags "#tag1,#tag2"
  python manage_tweets.py --interactive

This script reads/writes `tweets.json` in the same folder. It creates a timestamped backup
before any write.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any

ROOT = os.path.dirname(os.path.abspath(__file__))
TWEETS_FILE = os.path.join(ROOT, "tweets.json")


def load_tweets() -> List[Dict[str, Any]]:
    if not os.path.exists(TWEETS_FILE):
        return []
    with open(TWEETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def backup_tweets():
    if not os.path.exists(TWEETS_FILE):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(ROOT, f"tweets.json.bak.{ts}")
    shutil.copy2(TWEETS_FILE, dest)
    return dest


def save_tweets(tweets: List[Dict[str, Any]]):
    backup = backup_tweets()
    tmp = TWEETS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, TWEETS_FILE)
    return backup


def next_id(tweets: List[Dict[str, Any]]) -> str:
    # ids look like t1, t2... produce next numeric suffix
    maxn = 0
    for t in tweets:
        tid = t.get("id", "")
        if isinstance(tid, str) and tid.startswith("t"):
            try:
                n = int(tid[1:])
                if n > maxn:
                    maxn = n
            except Exception:
                continue
    return f"t{maxn + 1}"


def print_tweet(t: Dict[str, Any]):
    print(f'id: {t.get("id")}')
    print("enabled:", t.get("enabled", True))
    print("hashtags:", ", ".join(t.get("hashtags", [])))
    print("text:")
    print(t.get("text", ""))
    print("-" * 40)


def cmd_list(args):
    tweets = load_tweets()
    if not tweets:
        print("لا توجد تغريدات في ملف tweets.json")
        return
    for t in tweets:
        print_tweet(t)


def normalize_hashtags(s: str) -> List[str]:
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    out = []
    for p in parts:
        if not p.startswith("#"):
            p = "#" + p
        out.append(p)
    return out


def cmd_add(args):
    tweets = load_tweets()
    tid = next_id(tweets)
    hashtags = normalize_hashtags(args.hashtags or "")
    text = args.text or ""
    if not text:
        print("لا يوجد نص للتغريدة. استخدم --text أو --interactive")
        return
    new = {"id": tid, "text": text, "hashtags": hashtags, "enabled": True}
    tweets.append(new)
    backup = save_tweets(tweets)
    print(f"أضيفت التغريدة id={tid}")
    if backup:
        print(f"تم حفظ نسخة احتياطية: {os.path.basename(backup)}")


def find_index(tweets: List[Dict[str, Any]], tid: str):
    for i, t in enumerate(tweets):
        if t.get("id") == tid:
            return i
    return None


def cmd_delete(args):
    tweets = load_tweets()
    idx = find_index(tweets, args.id)
    if idx is None:
        print("لم يتم العثور على id")
        return
    removed = tweets.pop(idx)
    backup = save_tweets(tweets)
    print(f"حذفت التغريدة {removed.get('id')}")
    if backup:
        print(f"نسخة احتياطية: {os.path.basename(backup)}")


def cmd_edit(args):
    tweets = load_tweets()
    idx = find_index(tweets, args.id)
    if idx is None:
        print("لم يتم العثور على id")
        return
    t = tweets[idx]
    changed = False
    if args.text is not None:
        t["text"] = args.text
        changed = True
    if args.hashtags is not None:
        t["hashtags"] = normalize_hashtags(args.hashtags)
        changed = True
    if args.enabled is not None:
        t["enabled"] = args.enabled
        changed = True
    if changed:
        backup = save_tweets(tweets)
        print(f"تم تعديل التغريدة {t.get('id')}")
        if backup:
            print(f"نسخة احتياطية: {os.path.basename(backup)}")
    else:
        print("لم يتم تمرير أي تغيير. استخدم --text أو --hashtags أو --enabled/--disabled")


def cmd_interactive(args):
    print("وضع تفاعلي لإدارة التغريدات")
    print("1) إضافة تغريدة")
    print("2) تعديل تغريدة")
    print("3) حذف تغريدة")
    print("4) قائمة التغريدات")
    print("5) خروج")
    while True:
        try:
            opt = input("اختر خيار (1-5): ").strip()
        except EOFError:
            break
        if opt == "1":
            text = input("نص التغريدة (نص جديد):\n")
            tags = input("الهاشتاغات (مفصولة بفواصل, اختياري): ")
            class A:
                pass
            a = A()
            a.text = text
            a.hashtags = tags
            cmd_add(a)
        elif opt == "2":
            tid = input("id التغريدة المراد تعديلها: ").strip()
            tweets = load_tweets()
            idx = find_index(tweets, tid)
            if idx is None:
                print("لم يتم العثور على id")
                continue
            print_tweet(tweets[idx])
            newtext = input("نص جديد (اتركه فارغاً لعدم التغيير):\n")
            newtags = input("هاشتاغات جديدة (مفصولة بفواصل, اترك فارغاً لعدم التغيير): ")
            class B:
                pass
            b = B()
            b.id = tid
            b.text = newtext if newtext != "" else None
            b.hashtags = newtags if newtags != "" else None
            b.enabled = None
            cmd_edit(b)
        elif opt == "3":
            tid = input("id للحذف: ").strip()
            class C:
                pass
            c = C()
            c.id = tid
            cmd_delete(c)
        elif opt == "4":
            class D:
                pass
            d = D()
            cmd_list(d)
        elif opt == "5":
            break
        else:
            print("خيار غير صالح")


def main():
    parser = argparse.ArgumentParser(description="إدارة التغريدات في tweets.json")
    sub = parser.add_mutually_exclusive_group()
    sub.add_argument("--list", action="store_true", help="عرض جميع التغريدات")
    sub.add_argument("--interactive", action="store_true", help="وضع تفاعلي")
    parser.add_argument("--add", action="store_true", help="إضافة تغريدة (مع --text)")
    parser.add_argument("--delete", dest="delete", action="store_true", help="حذف تغريدة (مع --id)")
    parser.add_argument("--edit", dest="edit", action="store_true", help="تعديل تغريدة (مع --id)")
    parser.add_argument("--id", help="معرف التغريدة (مثل t1)")
    parser.add_argument("--text", help="نص التغريدة")
    parser.add_argument("--hashtags", help="قائمة الهاشتاغات مفصولة بفواصل (مثال: #a,#b أو a,b)")
    parser.add_argument("--enabled", type=lambda v: v.lower() in ("1","true","نعم","y","yes"), nargs='?', const=True, help="اجعل التغريدة مفعلة")
    parser.add_argument("--disabled", dest="disabled", action="store_true", help="اجعل التغريدة معطلة")
    args = parser.parse_args()

    # normalize enabled flag
    if getattr(args, "disabled", False):
        args.enabled = False

    if args.list:
        cmd_list(args)
        return
    if args.interactive:
        cmd_interactive(args)
        return
    if args.add:
        cmd_add(args)
        return
    if args.delete:
        if not args.id:
            print("--id مطلوب للحذف")
            return
        cmd_delete(args)
        return
    if args.edit:
        if not args.id:
            print("--id مطلوب للتعديل")
            return
        cmd_edit(args)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
