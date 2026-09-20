#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from datetime import datetime
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

CONFIG_DIR = os.path.expanduser('~/.config/tokyonight-hud')
GOAL_FILE = os.path.join(CONFIG_DIR, 'daily_goal.json')
HUD_SCRIPT = os.path.expanduser('~/.local/share/tokyonight-hud/tokyonight_hud.py')

DEFAULT_GOAL = {
    "goal": "Build clean code, solve core problems & stay focused",
    "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M')
}

def load_goal():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(GOAL_FILE):
        with open(GOAL_FILE, 'w') as f:
            json.dump(DEFAULT_GOAL, f, indent=2)
        return DEFAULT_GOAL
    try:
        with open(GOAL_FILE) as f:
            return json.load(f)
    except Exception:
        return DEFAULT_GOAL

def save_goal(goal_text):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = {
        "goal": goal_text.strip(),
        "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    with open(GOAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    return data

class EditGoalDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="Target Fokus & Prioritas Hari Ini")
        self.set_default_size(520, 320)
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
            color: #73daca;
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
            border-color: #73daca;
            box-shadow: 0 0 8px rgba(115, 218, 202, 0.3);
        }
        button.primary-btn {
            background-color: #73daca;
            color: #15161e;
            font-weight: bold;
            border-radius: 8px;
            padding: 8px 16px;
            border: none;
        }
        button.primary-btn:hover {
            background-color: #8df4e4;
        }
        button.secondary-btn {
            background-color: #24283b;
            color: #c0caf5;
            border-radius: 8px;
            padding: 8px 16px;
            border: 1px solid #414868;
        }
        button.secondary-btn:hover {
            background-color: #2f354f;
        }
        button.preset-btn {
            background-color: #1f2335;
            color: #7aa2f7;
            border-radius: 6px;
            padding: 4px 10px;
            border: 1px solid #292e42;
            font-size: 9pt;
        }
        button.preset-btn:hover {
            background-color: #292e42;
            color: #7dcfff;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        self.add(main_box)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label="🎯 SET TODAY'S MAIN FOCUS")
        title.get_style_context().add_class('header-title')
        title.set_xalign(0)
        sub = Gtk.Label(label="Tentukan target prioritas nomor 1 hari ini agar tetap fokus dan produktif.")
        sub.get_style_context().add_class('header-sub')
        sub.set_xalign(0)
        header_box.pack_start(title, False, False, 0)
        header_box.pack_start(sub, False, False, 0)
        main_box.pack_start(header_box, False, False, 0)

        # Input Goal Text
        input_label = Gtk.Label(label="Target Utama Hari Ini (Goal / Main Quest):")
        input_label.set_xalign(0)
        main_box.pack_start(input_label, False, False, 0)

        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_size_request(-1, 80)
        
        current_data = load_goal()
        self.text_buffer = self.text_view.get_buffer()
        self.text_buffer.set_text(current_data.get('goal', ''))
        main_box.pack_start(self.text_view, False, False, 0)

        # Quick preset buttons
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        p_label = Gtk.Label(label="Template cepat:")
        p_label.get_style_context().add_class('header-sub')
        preset_box.pack_start(p_label, False, False, 0)

        presets = [
            ("⚡ Feature Sprint", "Selesaikan fitur utama & integrasi API"),
            ("🐞 Bug Fixing", "Debug & resolve pending issue / error"),
            ("🚀 Code Refactor", "Refactor codebase & optimize performance")
        ]
        for name, text in presets:
            btn = Gtk.Button(label=name)
            btn.get_style_context().add_class('preset-btn')
            btn.connect('clicked', lambda b, t=text: self.text_buffer.set_text(t))
            preset_box.pack_start(btn, False, False, 0)
        main_box.pack_start(preset_box, False, False, 0)

        # Button Box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)

        btn_cancel = Gtk.Button(label="Batal")
        btn_cancel.get_style_context().add_class('secondary-btn')
        btn_cancel.connect('clicked', lambda b: self.destroy())

        btn_save = Gtk.Button(label="🎯 Simpan & Tampilkan")
        btn_save.get_style_context().add_class('primary-btn')
        btn_save.connect('clicked', self.on_save)

        btn_box.pack_start(btn_cancel, False, False, 0)
        btn_box.pack_start(btn_save, False, False, 0)
        main_box.pack_start(btn_box, False, False, 0)

    def on_save(self, widget):
        start_iter = self.text_buffer.get_start_iter()
        end_iter = self.text_buffer.get_end_iter()
        text = self.text_buffer.get_text(start_iter, end_iter, True).strip()

        if not text:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Teks Target Kosong"
            )
            dialog.format_secondary_text("Silakan masukkan teks target fokus Anda.")
            dialog.run()
            dialog.destroy()
            return

        save_goal(text)

        # Send notification
        try:
            subprocess.Popen([
                'notify-send',
                '-a', 'Tokyonight Daily Goal',
                '🎯 Target Hari Ini Diperbarui!',
                f'"{text}"\nTetap semangat & capai targetmu!',
                '-i', 'task-due',
                '-t', '4000'
            ])
        except Exception:
            pass

        # Trigger HUD update immediately
        if os.path.exists(HUD_SCRIPT):
            subprocess.Popen(['python3', HUD_SCRIPT, '--once'])

        self.destroy()

if __name__ == '__main__':
    win = EditGoalDialog()
    win.connect('destroy', Gtk.main_quit)
    win.show_all()
    Gtk.main()
