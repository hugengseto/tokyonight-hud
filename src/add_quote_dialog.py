#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio

CONFIG_DIR = os.path.expanduser('~/.config/tokyonight-hud')
QUOTES_FILE = os.path.join(CONFIG_DIR, 'quotes.json')
HUD_SCRIPT = os.path.expanduser('~/.local/share/tokyonight-hud/tokyonight_hud.py')

DEFAULT_QUOTES = [
    {"quote": "Talk is cheap. Show me the code.", "author": "Linus Torvalds"},
    {"quote": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
    {"quote": "Simplicity is prerequisite for reliability.", "author": "Edsger W. Dijkstra"},
    {"quote": "Make it work, make it right, make it fast.", "author": "Kent Beck"},
    {"quote": "Programs must be written for people to read, and only incidentally for machines to execute.", "author": "Harold Abelson"},
    {"quote": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "author": "Martin Fowler"},
    {"quote": "The only way to go fast, is to go well.", "author": "Robert C. Martin"},
    {"quote": "Premature optimization is the root of all evil.", "author": "Donald Knuth"},
    {"quote": "The best way to predict the future is to implement it.", "author": "David Heinemeier Hansson"},
    {"quote": "Fix the cause, not the symptom.", "author": "Steve Maguire"},
    {"quote": "Code is like humor. When you have to explain it, it’s bad.", "author": "Cory House"},
    {"quote": "Mastery is not about perfection. It is about staying on the path.", "author": "George Leonard"},
    {"quote": "Focus is a muscle. Train it every single day.", "author": "Engineering Mindset"}
]

def load_quotes():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(QUOTES_FILE):
        data = {"active_index": None, "quotes": DEFAULT_QUOTES}
        with open(QUOTES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return data
    try:
        with open(QUOTES_FILE) as f:
            return json.load(f)
    except Exception:
        return {"active_index": None, "quotes": DEFAULT_QUOTES}

def save_quotes(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(QUOTES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

class AddQuoteDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="Tambah Kutipan & Mindset Developer")
        self.set_default_size(520, 360)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

        # Tokyonight Dark Styling
        css_provider = Gtk.CssProvider()
        css = b"""
        window {
            background-color: #16161e;
            color: #c0caf5;
        }
        label {
            color: #7aa2f7;
            font-weight: bold;
        }
        .header-title {
            color: #7dcfff;
            font-size: 16pt;
            font-weight: bold;
        }
        .header-sub {
            color: #565f89;
            font-size: 10pt;
        }
        entry, textview, textview text {
            background-color: #1f2335;
            color: #c0caf5;
            border: 1.5px solid #292e42;
            border-radius: 8px;
            padding: 8px;
            font-size: 11pt;
        }
        entry:focus, textview text:focus {
            border-color: #7dcfff;
            box-shadow: 0 0 8px rgba(125, 207, 255, 0.3);
        }
        button.primary-btn {
            background-color: #7dcfff;
            color: #15161e;
            font-weight: bold;
            border-radius: 8px;
            padding: 8px 16px;
            border: none;
        }
        button.primary-btn:hover {
            background-color: #90d7ff;
        }
        button.secondary-btn {
            background-color: #24283b;
            color: #c0caf5;
            font-weight: bold;
            border-radius: 8px;
            padding: 8px 14px;
            border: 1px solid #414868;
        }
        button.secondary-btn:hover {
            background-color: #2f354f;
            border-color: #7aa2f7;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        vbox.set_border_width(20)
        self.add(vbox)

        # Header Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_title = Gtk.Label(label="💡 Tambah Mindset & Pola Pikir")
        lbl_title.get_style_context().add_class("header-title")
        lbl_title.set_xalign(0)
        title_box.pack_start(lbl_title, False, False, 0)

        lbl_sub = Gtk.Label(label="Kutipan ini akan langsung tampil di widget desktop Tokyonight Anda.")
        lbl_sub.get_style_context().add_class("header-sub")
        lbl_sub.set_xalign(0)
        title_box.pack_start(lbl_sub, False, False, 0)
        vbox.pack_start(title_box, False, False, 0)

        # Input Kutipan
        lbl_q = Gtk.Label(label="Kutipan (Quote):")
        lbl_q.set_xalign(0)
        vbox.pack_start(lbl_q, False, False, 0)

        self.txt_quote = Gtk.TextView()
        self.txt_quote.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txt_quote.set_size_request(-1, 75)
        self.quote_buffer = self.txt_quote.get_buffer()
        vbox.pack_start(self.txt_quote, False, False, 0)

        # Input Author
        lbl_a = Gtk.Label(label="Penulis / Tokoh (Author):")
        lbl_a.set_xalign(0)
        vbox.pack_start(lbl_a, False, False, 0)

        self.entry_author = Gtk.Entry()
        self.entry_author.set_placeholder_text("Contoh: Linus Torvalds, Steve Jobs, dll.")
        vbox.pack_start(self.entry_author, False, False, 0)

        # Buttons Box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_margin_top(8)

        btn_open_file = Gtk.Button(label="📂 Buka File JSON")
        btn_open_file.get_style_context().add_class("secondary-btn")
        btn_open_file.connect("clicked", self.on_open_file)
        btn_box.pack_start(btn_open_file, False, False, 0)

        spacer = Gtk.Box()
        btn_box.pack_start(spacer, True, True, 0)

        btn_cancel = Gtk.Button(label="Batal")
        btn_cancel.get_style_context().add_class("secondary-btn")
        btn_cancel.connect("clicked", lambda b: self.destroy())
        btn_box.pack_start(btn_cancel, False, False, 0)

        btn_save = Gtk.Button(label="💾 Simpan & Tampilkan")
        btn_save.get_style_context().add_class("primary-btn")
        btn_save.connect("clicked", self.on_save)
        btn_box.pack_start(btn_save, False, False, 0)

        vbox.pack_start(btn_box, False, False, 0)

    def on_open_file(self, btn):
        load_quotes() # ensure exists
        subprocess.Popen(['xdg-open', QUOTES_FILE])
        self.destroy()

    def on_save(self, btn):
        start_iter = self.quote_buffer.get_start_iter()
        end_iter = self.quote_buffer.get_end_iter()
        quote_text = self.quote_buffer.get_text(start_iter, end_iter, True).strip()
        author_text = self.entry_author.get_text().strip()

        if not quote_text:
            return

        if not author_text:
            author_text = "Anonymous"

        data = load_quotes()
        data['quotes'].append({
            "quote": quote_text,
            "author": author_text
        })
        # Set this newly added quote as currently active
        data['active_index'] = len(data['quotes']) - 1
        save_quotes(data)

        # Notify & Refresh desktop wallpaper
        try:
            subprocess.Popen(['python3', HUD_SCRIPT, '--once'])
            subprocess.Popen([
                'notify-send',
                '💡 Mindset Baru Ditambahkan!',
                f'"{quote_text}" — {author_text}',
                '-a', 'Tokyonight HUD'
            ])
        except Exception:
            pass

        self.destroy()

if __name__ == '__main__':
    win = AddQuoteDialog()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
