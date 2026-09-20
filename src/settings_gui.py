#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
from datetime import datetime

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
from PIL import Image, ImageOps

CONFIG_DIR = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')) + '/tokyonight-hud'
TITLE_FILE = os.path.join(CONFIG_DIR, 'hud_title.txt')
FOOTER_FILE = os.path.join(CONFIG_DIR, 'hud_footer.txt')
PHOTOS_JSON = os.path.join(CONFIG_DIR, 'motivation_photos.json')
PHOTO1_FILE = os.path.join(CONFIG_DIR, 'motivation_photo_1.jpg')
PHOTO2_FILE = os.path.join(CONFIG_DIR, 'motivation_photo_2.jpg')
GOAL_FILE = os.path.join(CONFIG_DIR, 'daily_goal.json')
QUOTES_FILE = os.path.join(CONFIG_DIR, 'quotes.json')

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_SCRIPT = os.path.join(APP_DIR, 'tokyonight_hud.py')
if not os.path.exists(ENGINE_SCRIPT):
    ENGINE_SCRIPT = os.path.join(os.path.expanduser('~/.local/share/tokyonight-hud'), 'tokyonight_hud.py')

os.makedirs(CONFIG_DIR, exist_ok=True)

class SettingsWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Tokyonight HUD Control Center")
        self.set_default_size(720, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(18)

        self.apply_theme()
        self.build_ui()
        self.load_data()

    def apply_theme(self):
        css = b"""
        window {
            background-color: #1a1b26;
            color: #c0caf5;
            font-family: 'Inter', 'Noto Sans', sans-serif;
        }
        .header-box {
            background: linear-gradient(135deg, #24283b, #1f2335);
            border: 1px solid #414868;
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 14px;
        }
        .section-card {
            background-color: #24283b;
            border: 1px solid #3b4261;
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 12px;
        }
        label.section-title {
            color: #7dcfff;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 6px;
        }
        entry {
            background-color: #1a1b26;
            color: #c0caf5;
            border: 1px solid #414868;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
        }
        entry:focus {
            border-color: #7aa2f7;
            box-shadow: 0 0 0 1px #7aa2f7;
        }
        button.primary-btn {
            background: linear-gradient(135deg, #7aa2f7, #3d59a1);
            color: #ffffff;
            font-weight: bold;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
        }
        button.primary-btn:hover {
            background: linear-gradient(135deg, #89b4fa, #7aa2f7);
        }
        button.action-btn {
            background-color: #1f2335;
            color: #c0caf5;
            border: 1px solid #414868;
            border-radius: 8px;
            padding: 6px 14px;
        }
        button.action-btn:hover {
            background-color: #292e42;
            border-color: #7aa2f7;
        }
        button.danger-btn {
            background-color: #2b1d28;
            color: #f7768e;
            border: 1px solid #f7768e;
            border-radius: 8px;
            padding: 6px 12px;
        }
        button.danger-btn:hover {
            background-color: #492635;
        }
        notebook tab {
            background-color: #1f2335;
            color: #a9b1d6;
            padding: 8px 16px;
            border-radius: 8px 8px 0 0;
            font-weight: bold;
        }
        notebook tab:checked {
            background-color: #24283b;
            color: #7dcfff;
            border-bottom: 2px solid #7dcfff;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)

        # Header Box
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        hdr_box.get_style_context().add_class('header-box')

        hdr_icon = Gtk.Image.new_from_icon_name("preferences-desktop-wallpaper", Gtk.IconSize.DIALOG)
        hdr_box.pack_start(hdr_icon, False, False, 0)

        hdr_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_title = Gtk.Label(xalign=0)
        lbl_title.set_markup("<span size='large' weight='bold' color='#7dcfff'>Tokyonight HUD Control Center</span>")
        lbl_subtitle = Gtk.Label(xalign=0)
        lbl_subtitle.set_markup("<span size='small' color='#9aa5ce'>Real-time desktop system overview &amp; motivation widgets</span>")
        hdr_vbox.pack_start(lbl_title, False, False, 0)
        hdr_vbox.pack_start(lbl_subtitle, False, False, 0)
        hdr_box.pack_start(hdr_vbox, True, True, 0)

        # Service Status Indicator
        self.lbl_status = Gtk.Label()
        self.update_service_status()
        hdr_box.pack_end(self.lbl_status, False, False, 4)

        main_box.pack_start(hdr_box, False, False, 0)

        # Notebook / Tabs
        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)

        # Tab 1: General & Identity
        tab_general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_general.set_border_width(12)

        # HUD Title
        card_title = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_title.get_style_context().add_class('section-card')
        lbl = Gtk.Label(label="Header Display Title (Main Identity):", xalign=0)
        lbl.get_style_context().add_class('section-title')
        card_title.pack_start(lbl, False, False, 0)
        self.entry_title = Gtk.Entry()
        self.entry_title.set_placeholder_text("e.g. HUGENGSETO or SYSTEM OVERVIEW")
        card_title.pack_start(self.entry_title, False, False, 0)
        tab_general.pack_start(card_title, False, False, 0)

        # HUD Footer Milestone
        card_footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_footer.get_style_context().add_class('section-card')
        lbl_f = Gtk.Label(label="Bottom Milestone Badge Text:", xalign=0)
        lbl_f.get_style_context().add_class('section-title')
        card_footer.pack_start(lbl_f, False, False, 0)
        self.entry_footer = Gtk.Entry()
        self.entry_footer.set_placeholder_text("Leave blank for automatic Linux uptime / milestone calculation")
        card_footer.pack_start(self.entry_footer, False, False, 0)
        tab_general.pack_start(card_footer, False, False, 0)

        notebook.append_page(tab_general, Gtk.Label(label="Identity"))

        # Tab 2: Photos (Motivation Gallery)
        tab_photos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab_photos.set_border_width(12)

        photos_desc = Gtk.Label(xalign=0)
        photos_desc.set_markup("<span color='#9aa5ce'>Display up to 2 photos centered side-by-side at the bottom of the HUD card.</span>")
        tab_photos.pack_start(photos_desc, False, False, 0)

        h_slots = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        tab_photos.pack_start(h_slots, True, True, 0)

        # Slot 1
        slot1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        slot1_box.get_style_context().add_class('section-card')
        lbl_s1 = Gtk.Label(label="Photo Slot 1 (Left)", xalign=0.5)
        lbl_s1.get_style_context().add_class('section-title')
        slot1_box.pack_start(lbl_s1, False, False, 0)

        self.img1 = Gtk.Image()
        self.img1.set_size_request(150, 180)
        slot1_box.pack_start(self.img1, True, True, 0)

        btn_box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_pick1 = Gtk.Button(label="Choose Image...")
        btn_pick1.get_style_context().add_class('action-btn')
        btn_pick1.connect('clicked', lambda w: self.pick_image(1))
        btn_clear1 = Gtk.Button(label="Clear")
        btn_clear1.get_style_context().add_class('danger-btn')
        btn_clear1.connect('clicked', lambda w: self.clear_image(1))
        btn_box1.pack_start(btn_pick1, True, True, 0)
        btn_box1.pack_start(btn_clear1, False, False, 0)
        slot1_box.pack_start(btn_box1, False, False, 0)
        h_slots.pack_start(slot1_box, True, True, 0)

        # Slot 2
        slot2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        slot2_box.get_style_context().add_class('section-card')
        lbl_s2 = Gtk.Label(label="Photo Slot 2 (Right)", xalign=0.5)
        lbl_s2.get_style_context().add_class('section-title')
        slot2_box.pack_start(lbl_s2, False, False, 0)

        self.img2 = Gtk.Image()
        self.img2.set_size_request(150, 180)
        slot2_box.pack_start(self.img2, True, True, 0)

        btn_box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_pick2 = Gtk.Button(label="Choose Image...")
        btn_pick2.get_style_context().add_class('action-btn')
        btn_pick2.connect('clicked', lambda w: self.pick_image(2))
        btn_clear2 = Gtk.Button(label="Clear")
        btn_clear2.get_style_context().add_class('danger-btn')
        btn_clear2.connect('clicked', lambda w: self.clear_image(2))
        btn_box2.pack_start(btn_pick2, True, True, 0)
        btn_box2.pack_start(btn_clear2, False, False, 0)
        slot2_box.pack_start(btn_box2, False, False, 0)
        h_slots.pack_start(slot2_box, True, True, 0)

        notebook.append_page(tab_photos, Gtk.Label(label="Gallery"))

        # Tab 3: Goals & Focus
        tab_goal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_goal.set_border_width(12)

        card_g = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_g.get_style_context().add_class('section-card')
        lbl_g = Gtk.Label(label="🎯 Today's Main Sprint Focus & Goal:", xalign=0)
        lbl_g.get_style_context().add_class('section-title')
        card_g.pack_start(lbl_g, False, False, 0)

        self.entry_goal = Gtk.Entry()
        self.entry_goal.set_placeholder_text("e.g. Build clean code, solve core problems & stay focused")
        card_g.pack_start(self.entry_goal, False, False, 0)
        tab_goal.pack_start(card_g, False, False, 0)

        notebook.append_page(tab_goal, Gtk.Label(label="Daily Goal"))

        # Tab 4: Maintenance & Actions
        tab_maint = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_maint.set_border_width(12)

        card_act = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card_act.get_style_context().add_class('section-card')
        lbl_act = Gtk.Label(label="⚡ System Operations & Quick Actions", xalign=0)
        lbl_act.get_style_context().add_class('section-title')
        card_act.pack_start(lbl_act, False, False, 0)

        btn_clean = Gtk.Button(label="🧹 Run Safe System Junk Cleaner")
        btn_clean.get_style_context().add_class('action-btn')
        btn_clean.connect('clicked', self.on_clean_junk)
        card_act.pack_start(btn_clean, False, False, 0)

        btn_restart = Gtk.Button(label="🔄 Restart Background Service (tokyonight-hud)")
        btn_restart.get_style_context().add_class('action-btn')
        btn_restart.connect('clicked', self.on_restart_service)
        card_act.pack_start(btn_restart, False, False, 0)

        tab_maint.pack_start(card_act, False, False, 0)
        notebook.append_page(tab_maint, Gtk.Label(label="Maintenance"))

        # Bottom Bar Buttons
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_box.pack_end(bottom_box, False, False, 6)

        btn_save = Gtk.Button(label="💾 Save & Apply Immediately")
        btn_save.get_style_context().add_class('primary-btn')
        btn_save.connect('clicked', self.on_save)
        bottom_box.pack_end(btn_save, False, False, 0)

        btn_close = Gtk.Button(label="Close")
        btn_close.get_style_context().add_class('action-btn')
        btn_close.connect('clicked', lambda w: self.destroy())
        bottom_box.pack_end(btn_close, False, False, 0)

        self.pending_photo1 = None
        self.pending_photo2 = None

    def update_service_status(self):
        is_active = False
        try:
            res = subprocess.run(['systemctl', '--user', 'is-active', 'tokyonight-hud.service'],
                                 capture_output=True, text=True)
            is_active = res.stdout.strip() == 'active'
        except Exception:
            pass

        if is_active:
            self.lbl_status.set_markup("<span color='#9ece6a' weight='bold'>● Service Active</span>")
        else:
            self.lbl_status.set_markup("<span color='#f7768e' weight='bold'>○ Service Stopped</span>")

    def load_data(self):
        # Title
        if os.path.exists(TITLE_FILE):
            try:
                with open(TITLE_FILE) as f:
                    self.entry_title.set_text(f.read().strip())
            except Exception:
                pass
        else:
            user = os.environ.get('USER', 'SYSTEM').upper()
            self.entry_title.set_text(user if user != 'ROOT' else 'SYSTEM OVERVIEW')

        # Footer
        if os.path.exists(FOOTER_FILE):
            try:
                with open(FOOTER_FILE) as f:
                    self.entry_footer.set_text(f.read().strip())
            except Exception:
                pass

        # Goal
        if os.path.exists(GOAL_FILE):
            try:
                with open(GOAL_FILE) as f:
                    d = json.load(f)
                    self.entry_goal.set_text(d.get('goal', ''))
            except Exception:
                pass

        # Photos
        self.pending_photo1 = PHOTO1_FILE if os.path.exists(PHOTO1_FILE) else None
        self.pending_photo2 = PHOTO2_FILE if os.path.exists(PHOTO2_FILE) else None

        if os.path.exists(PHOTOS_JSON):
            try:
                with open(PHOTOS_JSON) as f:
                    d = json.load(f)
                    p1 = d.get('photo_1')
                    p2 = d.get('photo_2')
                    if p1 and os.path.exists(p1):
                        self.pending_photo1 = p1
                    elif p1 is None and 'photo_1' in d:
                        self.pending_photo1 = None

                    if p2 and os.path.exists(p2):
                        self.pending_photo2 = p2
                    elif p2 is None and 'photo_2' in d:
                        self.pending_photo2 = None
            except Exception:
                pass

        self.update_thumbnail(1, self.pending_photo1)
        self.update_thumbnail(2, self.pending_photo2)

    def update_thumbnail(self, slot, path):
        img_widget = self.img1 if slot == 1 else self.img2
        if path and os.path.exists(path):
            try:
                im = Image.open(path)
                im = ImageOps.exif_transpose(im)
                im.thumbnail((180, 180), Image.Resampling.LANCZOS)
                tmp_thumb = os.path.join(CONFIG_DIR, f'.thumb_{slot}.png')
                im.save(tmp_thumb, 'PNG')
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(tmp_thumb)
                img_widget.set_from_pixbuf(pixbuf)
                return
            except Exception as e:
                print(f"Error loading thumb {slot}: {e}", file=sys.stderr)
        img_widget.set_from_icon_name('image-missing', Gtk.IconSize.DIALOG)

    def pick_image(self, slot):
        dialog = Gtk.FileChooserDialog(
            title=f"Select Photo for Slot {slot}",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        filt = Gtk.FileFilter()
        filt.set_name("Images (*.jpg, *.jpeg, *.png, *.webp)")
        filt.add_mime_type("image/jpeg")
        filt.add_mime_type("image/png")
        filt.add_mime_type("image/webp")
        dialog.add_filter(filt)

        res = dialog.run()
        if res == Gtk.ResponseType.OK:
            chosen = dialog.get_filename()
            if slot == 1:
                self.pending_photo1 = chosen
            else:
                self.pending_photo2 = chosen
            self.update_thumbnail(slot, chosen)
        dialog.destroy()

    def clear_image(self, slot):
        if slot == 1:
            self.pending_photo1 = None
        else:
            self.pending_photo2 = None
        self.update_thumbnail(slot, None)

    def on_clean_junk(self, widget):
        cleaner = os.path.join(APP_DIR, 'clean_system_junk.py')
        if os.path.exists(cleaner):
            subprocess.Popen(['python3', cleaner])

    def on_restart_service(self, widget):
        subprocess.run(['systemctl', '--user', 'restart', 'tokyonight-hud.service'])
        GLib.timeout_add(1000, self.update_service_status)

    def on_save(self, widget):
        # 1. Save Title
        new_title = self.entry_title.get_text().strip()
        if new_title:
            with open(TITLE_FILE, 'w') as f:
                f.write(new_title + '\n')

        # 2. Save Footer
        new_footer = self.entry_footer.get_text().strip()
        if new_footer:
            with open(FOOTER_FILE, 'w') as f:
                f.write(new_footer + '\n')
        elif os.path.exists(FOOTER_FILE):
            try:
                os.remove(FOOTER_FILE)
            except Exception:
                pass

        # 3. Save Goal
        new_goal = self.entry_goal.get_text().strip()
        if new_goal:
            with open(GOAL_FILE, 'w') as f:
                json.dump({'goal': new_goal, 'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')}, f, indent=2)

        # 4. Save Photos
        # Copy to config files if changed
        if self.pending_photo1 and self.pending_photo1 != PHOTO1_FILE:
            try:
                shutil.copy2(self.pending_photo1, PHOTO1_FILE)
                self.pending_photo1 = PHOTO1_FILE
            except Exception as e:
                print(f"Error copying photo 1: {e}", file=sys.stderr)
        elif not self.pending_photo1 and os.path.exists(PHOTO1_FILE):
            try:
                os.remove(PHOTO1_FILE)
            except Exception:
                pass

        if self.pending_photo2 and self.pending_photo2 != PHOTO2_FILE:
            try:
                shutil.copy2(self.pending_photo2, PHOTO2_FILE)
                self.pending_photo2 = PHOTO2_FILE
            except Exception as e:
                print(f"Error copying photo 2: {e}", file=sys.stderr)
        elif not self.pending_photo2 and os.path.exists(PHOTO2_FILE):
            try:
                os.remove(PHOTO2_FILE)
            except Exception:
                pass

        with open(PHOTOS_JSON, 'w') as f:
            json.dump({
                'title': new_title,
                'photo_1': self.pending_photo1,
                'photo_2': self.pending_photo2,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
            }, f, indent=2)

        # 5. Trigger HUD Reload
        if os.path.exists(ENGINE_SCRIPT):
            subprocess.Popen(['python3', ENGINE_SCRIPT, '--once'])

        # Notify user
        try:
            subprocess.run([
                'notify-send',
                '-a', 'Tokyonight HUD',
                '✨ Settings Applied',
                'Your Tokyo Night HUD configuration was saved and reloaded!',
                '-i', 'preferences-desktop-wallpaper',
                '-t', '3500'
            ])
        except Exception:
            pass

        self.destroy()

def main():
    win = SettingsWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()
