# -*- coding: utf-8 -*-
"""
Simple desktop GUI (Tkinter) to manage tweets.json locally.

Usage:
  python manage_tweets_gui.py

This GUI reuses helper functions from `manage_tweets.py` (load_tweets/save_tweets/next_id/normalize_hashtags).
"""
from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# try to import helpers from manage_tweets.py in the same folder
try:
    from manage_tweets import load_tweets, save_tweets, next_id, normalize_hashtags
except Exception:
    # fallback: minimal local implementations if import fails
    import json
    from datetime import datetime
    import shutil

    ROOT = os.path.dirname(os.path.abspath(__file__))
    TWEETS_FILE = os.path.join(ROOT, "tweets.json")

    def load_tweets():
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

    def save_tweets(tweets):
        backup = backup_tweets()
        tmp = TWEETS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, TWEETS_FILE)
        return backup

    def next_id(tweets):
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

    def normalize_hashtags(s: str):
        if not s:
            return []
        parts = [p.strip() for p in s.split(",") if p.strip()]
        out = []
        for p in parts:
            if not p.startswith("#"):
                p = "#" + p
            out.append(p)
        return out


class TweetManagerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("إدارة التغريدات")
        self.geometry("900x560")
        self.resizable(True, True)

        self.tweets = []

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        main = ttk.Frame(self, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y)

        lbl = ttk.Label(left, text="قائمة التغريدات")
        lbl.pack(anchor=tk.W)

        self.listbox = tk.Listbox(left, width=40, activestyle='none')
        self.listbox.pack(fill=tk.Y, expand=True, pady=6)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(btn_frame, text="تحديث", command=self.refresh_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="إضافة", command=self.add_tweet_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="تعديل", command=self.edit_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="حذف", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="تبديل الحالة", command=self.toggle_enabled_selected).pack(side=tk.LEFT, padx=2)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12,0))

        meta = ttk.Frame(right)
        meta.pack(fill=tk.X)
        self.id_var = tk.StringVar()
        ttk.Label(meta, text="id:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(meta, textvariable=self.id_var).grid(row=0, column=1, sticky=tk.W)
        self.enabled_var = tk.StringVar()
        ttk.Label(meta, text="enabled:").grid(row=0, column=2, sticky=tk.W, padx=(12,0))
        ttk.Label(meta, textvariable=self.enabled_var).grid(row=0, column=3, sticky=tk.W)
        self.tags_var = tk.StringVar()
        ttk.Label(meta, text="hashtags:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(meta, textvariable=self.tags_var).grid(row=1, column=1, columnspan=3, sticky=tk.W)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        ttk.Label(right, text="النص:").pack(anchor=tk.W)
        self.text_widget = ScrolledText(right, height=20, wrap=tk.WORD)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.configure(state=tk.DISABLED)

        bottom = ttk.Frame(right)
        bottom.pack(fill=tk.X, pady=6)
        ttk.Button(bottom, text="حفظ" , command=self.save_all).pack(side=tk.RIGHT)

        # --- Scheduler panel ---
        sched = ttk.Labelframe(right, text="جدولة النشر")
        sched.pack(fill=tk.X, pady=(8,0))
        self.interval_var = tk.StringVar(value="3600")
        ttk.Label(sched, text="فاصل النشر (ثواني):").grid(row=0, column=0, sticky=tk.W, padx=6, pady=6)
        ttk.Entry(sched, textvariable=self.interval_var, width=12).grid(row=0, column=1, sticky=tk.W)
        ttk.Button(sched, text="حفظ الفاصل", command=self.save_interval).grid(row=0, column=2, padx=6)

        ttk.Label(sched, text="آخر نشر:").grid(row=1, column=0, sticky=tk.W, padx=6)
        self.last_post_var = tk.StringVar(value="---")
        ttk.Label(sched, textvariable=self.last_post_var).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(sched, text="الزمن المتبقي:" ).grid(row=2, column=0, sticky=tk.W, padx=6)
        self.countdown_var = tk.StringVar(value="--:--:--")
        ttk.Label(sched, textvariable=self.countdown_var).grid(row=2, column=1, sticky=tk.W)

        ttk.Button(sched, text="تم النشر الآن (تعيين آخر وقت)", command=self.mark_posted_now).grid(row=3, column=0, columnspan=2, pady=6)
        ttk.Button(sched, text="صيغة النشر للتغريدة التالية", command=self.show_next_publish_text).grid(row=3, column=2, padx=6)

        # scheduler internal state
        self.last_post_ts = None
        self.interval_seconds = int(self.interval_var.get()) if self.interval_var.get().isdigit() else 3600
        self._load_last_post_from_state()
        self._tick_countdown()

    def refresh_list(self):
        try:
            self.tweets = load_tweets() or []
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في قراءة tweets.json:\n{e}")
            self.tweets = []
        self.listbox.delete(0, tk.END)
        for t in self.tweets:
            preview = t.get("text", "").splitlines()
            first = preview[0] if preview else ""
            label = f"{t.get('id')} - {first[:60]}"
            self.listbox.insert(tk.END, label)
        self.clear_details()

    def clear_details(self):
        self.id_var.set("")
        self.enabled_var.set("")
        self.tags_var.set("")
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.configure(state=tk.DISABLED)

    def on_select(self, evt=None):
        sel = self.listbox.curselection()
        if not sel:
            self.clear_details()
            return
        idx = sel[0]
        t = self.tweets[idx]
        self.id_var.set(t.get("id"))
        self.enabled_var.set(str(t.get("enabled", True)))
        self.tags_var.set(", ".join(t.get("hashtags", [])))
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, t.get("text", ""))
        self.text_widget.configure(state=tk.DISABLED)

    def add_tweet_dialog(self):
        Dialog(self, on_save=self._add_tweet)

    def _add_tweet(self, text, hashtags, enabled):
        try:
            tweets = load_tweets() or []
            tid = next_id(tweets)
            tags = normalize_hashtags(hashtags or "")
            new = {"id": tid, "text": text or "", "hashtags": tags, "enabled": bool(enabled)}
            tweets.append(new)
            save_tweets(tweets)
            self.refresh_list()
            messagebox.showinfo("تم", f"أضيفت التغريدة {tid}")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def edit_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("تنبيه", "اختر تغريدة أولاً")
            return
        idx = sel[0]
        t = self.tweets[idx]
        Dialog(self, initial=t, on_save=lambda text, hashtags, enabled: self._edit_tweet(t.get('id'), text, hashtags, enabled))

    def _edit_tweet(self, tid, text, hashtags, enabled):
        try:
            tweets = load_tweets() or []
            for t in tweets:
                if t.get('id') == tid:
                    t['text'] = text or ""
                    t['hashtags'] = normalize_hashtags(hashtags or "")
                    t['enabled'] = bool(enabled)
                    break
            else:
                messagebox.showerror("خطأ", "لم يتم العثور على التغريدة")
                return
            save_tweets(tweets)
            self.refresh_list()
            messagebox.showinfo("تم", f"تم تعديل {tid}")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("تنبيه", "اختر تغريدة للحذف")
            return
        idx = sel[0]
        t = self.tweets[idx]
        if not messagebox.askyesno("تأكيد", f"هل تريد حذف {t.get('id')}؟"):
            return
        try:
            tweets = load_tweets() or []
            tweets = [x for x in tweets if x.get('id') != t.get('id')]
            save_tweets(tweets)
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def toggle_enabled_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("تنبيه", "اختر تغريدة أولاً")
            return
        idx = sel[0]
        t = self.tweets[idx]
        try:
            tweets = load_tweets() or []
            for x in tweets:
                if x.get('id') == t.get('id'):
                    x['enabled'] = not bool(x.get('enabled', True))
                    break
            save_tweets(tweets)
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def save_all(self):
        # simply reload and save to ensure formatting/backup; mainly placeholder
        try:
            tweets = load_tweets() or []
            save_tweets(tweets)
            messagebox.showinfo("تم", "تم الحفظ (تم إنشاء نسخة احتياطية إذا لزم)")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    # --- Scheduler helpers ---
    def _load_last_post_from_state(self):
        # try to read storage_state.json for a last posted timestamp if present
        try:
            import json
            root = os.path.dirname(os.path.abspath(__file__))
            state_file = os.path.join(root, "storage_state.json")
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    st = json.load(f)
                # heuristic: look for a top-level field 'last_post_ts' or similar
                # if not present, leave None
                lp = st.get("last_post_ts") if isinstance(st, dict) else None
                if lp:
                    try:
                        # assume seconds since epoch
                        import datetime
                        self.last_post_ts = float(lp)
                        self.last_post_var.set(datetime.datetime.fromtimestamp(self.last_post_ts).isoformat(sep=' '))
                        return
                    except Exception:
                        pass
        except Exception:
            pass
        # fallback: not set
        self.last_post_var.set("---")

    def save_interval(self):
        v = self.interval_var.get().strip()
        try:
            s = int(v)
            if s <= 0:
                raise ValueError()
            self.interval_seconds = s
            messagebox.showinfo("تم", f"تم تعيين الفاصل إلى {s} ثانية")
        except Exception:
            messagebox.showerror("خطأ", "أدخل رقماً صحيحاً للفاصل بالثواني")

    def mark_posted_now(self):
        import time, json
        ts = time.time()
        self.last_post_ts = ts
        import datetime
        self.last_post_var.set(datetime.datetime.fromtimestamp(ts).isoformat(sep=' '))
        # persist to storage_state.json (best-effort)
        try:
            root = os.path.dirname(os.path.abspath(__file__))
            state_file = os.path.join(root, "storage_state.json")
            data = {}
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            data["last_post_ts"] = ts
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("تم", "تعيين آخر وقت النشر إلى الآن وتم الحفظ في storage_state.json")
        except Exception as e:
            messagebox.showwarning("تحذير", f"تم التعيين محلياً لكن لم يتم الحفظ:\n{e}")

    def _tick_countdown(self):
        import time, datetime
        if self.last_post_ts is None:
            self.countdown_var.set("--:--:--")
        else:
            elapsed = time.time() - float(self.last_post_ts)
            remaining = int(self.interval_seconds - elapsed)
            if remaining <= 0:
                self.countdown_var.set("جاهز للنشر")
            else:
                hrs = remaining // 3600
                mins = (remaining % 3600) // 60
                secs = remaining % 60
                self.countdown_var.set(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        # schedule next tick
        self.after(1000, self._tick_countdown)

    def show_next_publish_text(self):
        # determine next enabled tweet and show formatted publish text
        tweets = [t for t in (load_tweets() or []) if t.get('enabled', True)]
        if not tweets:
            messagebox.showinfo("معلومة", "لا توجد تغريدات مفعلة")
            return
        # use first tweet in list as next
        nxt = tweets[0]
        full_text = self._format_publish_text(nxt)
        # show in a dialog with option to copy to clipboard
        dlg = tk.Toplevel(self)
        dlg.title("صيغة النشر")
        txt = ScrolledText(dlg, height=12, width=80, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt.insert(tk.END, full_text)
        txt.configure(state=tk.DISABLED)
        def _copy():
            try:
                self.clipboard_clear()
                self.clipboard_append(full_text)
                messagebox.showinfo("تم", "نسخ النص إلى الحافظة")
            except Exception as e:
                messagebox.showerror("خطأ", str(e))
        btns = ttk.Frame(dlg)
        btns.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(btns, text="نسخ إلى الحافظة", command=_copy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="إغلاق", command=dlg.destroy).pack(side=tk.RIGHT)

    def _format_publish_text(self, tweet: dict) -> str:
        # Compose a friendly publish string including hashtags and separators
        text = tweet.get('text', '').strip()
        tags = " ".join(tweet.get('hashtags', []))
        lines = []
        lines.append(text)
        if tags:
            lines.append("")
            lines.append(tags)
        lines.append("")
        lines.append(f"[id: {tweet.get('id')}]")
        return "\n".join(lines)


class Dialog(tk.Toplevel):
    def __init__(self, parent, initial=None, on_save=None):
        super().__init__(parent)
        self.title("إضافة/تعديل تغريدة")
        self.transient(parent)
        self.on_save = on_save
        self.initial = initial or {}

        ttk.Label(self, text="النص:").pack(anchor=tk.W, padx=8, pady=(8,0))
        self.text = ScrolledText(self, height=10, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.text.insert(tk.END, self.initial.get('text',''))

        frm = ttk.Frame(self)
        frm.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(frm, text="الهاشتاغات (مفصولة بفواصل):").grid(row=0, column=0, sticky=tk.W)
        self.tags_ent = ttk.Entry(frm)
        self.tags_ent.grid(row=0, column=1, sticky=tk.EW, padx=(6,0))
        self.tags_ent.insert(0, ", ".join(self.initial.get('hashtags', [])))
        frm.columnconfigure(1, weight=1)

        self.enabled_var = tk.BooleanVar(value=bool(self.initial.get('enabled', True)))
        ttk.Checkbutton(self, text="مفعلة", variable=self.enabled_var).pack(anchor=tk.W, padx=8)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=8, padx=8)
        ttk.Button(btns, text="إلغاء", command=self.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="حفظ", command=self._do_save).pack(side=tk.RIGHT)

        self.grab_set()
        self.geometry("700x420")
        self.focus()

    def _do_save(self):
        text = self.text.get("1.0", tk.END).rstrip('\n')
        tags = self.tags_ent.get()
        enabled = self.enabled_var.get()
        if self.on_save:
            self.on_save(text, tags, enabled)
        self.destroy()


def main():
    app = TweetManagerGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
