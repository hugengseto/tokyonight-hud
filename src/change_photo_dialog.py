#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

CONFIG_DIR = os.path.expanduser('~/.config/tokyonight-hud')
TITLE_FILE = os.path.join(CONFIG_DIR, 'hud_title.txt')
PHOTO1_FILE = os.path.join(CONFIG_DIR, 'motivation_photo_1.jpg')
PHOTO2_FILE = os.path.join(CONFIG_DIR, 'motivation_photo_2.jpg')
JSON_FILE = os.path.join(CONFIG_DIR, 'motivation_photos.json')
HUD_SCRIPT = os.path.expanduser('~/.local/share/tokyonight-hud/tokyonight_hud.py')

def load_title():
    if os.path.exists(TITLE_FILE):
        try:
            with open(TITLE_FILE) as f:
                t = f.read().strip()
                if t:
                    return t
        except Exception:
            pass
    return "HUGENGSETO"

def load_photos():
    default_cfg = {
        "photo_1": PHOTO1_FILE if os.path.exists(PHOTO1_FILE) else None,
        "photo_2": PHOTO2_FILE if os.path.exists(PHOTO2_FILE) else None
    }
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE) as f:
                data = json.load(f)
                return {
                    "photo_1": data.get("photo_1"),
                    "photo_2": data.get("photo_2")
                }
        except Exception:
            pass
    return default_cfg

class ChangePhotoDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="Pengaturan Judul & Foto Desktop HUD")
        self.set_default_size(560, 520)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

        self.current_title = load_title()
        photos = load_photos()
        self.photo1_path = photos.get("photo_1")
        self.photo2_path = photos.get("photo_2")

        # Validate existence
        if self.photo1_path and not os.path.exists(self.photo1_path):
            self.photo1_path = None
        if self.photo2_path and not os.path.exists(self.photo2_path):
            self.photo2_path = None

        # Tokyonight Dark Theme Styling
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
            color: #ff9e64;
            font-size: 20px;
            font-weight: bold;
        }
        .header-desc {
            color: #a9b1d6;
            font-size: 13px;
        }
        .section-label {
            color: #7dcfff;
            font-size: 13px;
            font-weight: bold;
            margin-top: 4px;
        }
        entry {
            background-color: #1f2335;
            color: #ffffff;
            border: 1.5px solid #3b4261;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
        }
        entry:focus {
            border-color: #ff9e64;
            box-shadow: 0 0 6px rgba(255, 158, 100, 0.4);
        }
        .preview-frame {
            border: 2px solid #e0af68;
            border-radius: 12px;
            background-color: #1a1b26;
        }
        .btn-choose {
            background-color: #24283b;
            color: #ff9e64;
            border: 1.5px solid #ff9e64;
            border-radius: 8px;
            font-weight: bold;
            padding: 6px 12px;
        }
        .btn-choose:hover {
            background-color: rgba(255, 158, 100, 0.25);
        }
        .btn-remove {
            background-color: #24283b;
            color: #f7768e;
            border: 1px solid #f7768e;
            border-radius: 8px;
            font-size: 12px;
            padding: 4px 10px;
        }
        .btn-remove:hover {
            background-color: rgba(247, 118, 142, 0.25);
        }
        .info-pill {
            background-color: rgba(122, 162, 247, 0.12);
            border: 1px solid rgba(122, 162, 247, 0.35);
            border-radius: 10px;
            padding: 10px 14px;
        }
        .btn-save {
            background-color: #ff9e64;
            color: #1a1b26;
            font-weight: bold;
            font-size: 14px;
            border-radius: 10px;
            border: none;
            padding: 10px 22px;
        }
        .btn-save:hover {
            background-color: #ffb47e;
        }
        .btn-cancel {
            background-color: #292e42;
            color: #c0caf5;
            font-weight: bold;
            font-size: 14px;
            border-radius: 10px;
            border: 1px solid #414868;
            padding: 10px 18px;
        }
        .btn-cancel:hover {
            background-color: #3b4261;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_left(20)
        main_box.set_margin_right(20)
        self.add(main_box)

        # Header
        head_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_lbl = Gtk.Label(label="⚙️ Pengaturan Judul & Galeri Foto HUD")
        title_lbl.get_style_context().add_class('header-title')
        title_lbl.set_xalign(0.0)
        head_box.pack_start(title_lbl, False, False, 0)

        desc_lbl = Gtk.Label(label="Ubah nama header utama dan pasang hingga 2 foto motivasi pribadi.")
        desc_lbl.get_style_context().add_class('header-desc')
        desc_lbl.set_xalign(0.0)
        head_box.pack_start(desc_lbl, False, False, 0)
        main_box.pack_start(head_box, False, False, 0)

        # 1. Judul Header HUD
        t_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        t_lbl = Gtk.Label(label="🏷️ Judul Header Utama (Menggantikan 'SYSTEM OVERVIEW'):")
        t_lbl.get_style_context().add_class('section-label')
        t_lbl.set_xalign(0.0)
        t_box.pack_start(t_lbl, False, False, 0)

        self.title_entry = Gtk.Entry()
        self.title_entry.set_text(self.current_title)
        self.title_entry.set_placeholder_text("Contoh: HUGENGSETO atau WORKSPACE")
        t_box.pack_start(self.title_entry, False, False, 0)
        main_box.pack_start(t_box, False, False, 0)

        # Photos Row (Photo 1 and Photo 2 side by side)
        photos_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        photos_row.set_homogeneous(True)

        # === SLOT 1 ===
        slot1_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        s1_lbl = Gtk.Label(label="📷 Foto 1 (Utama):")
        s1_lbl.get_style_context().add_class('section-label')
        s1_lbl.set_xalign(0.0)
        slot1_box.pack_start(s1_lbl, False, False, 0)

        self.img1_preview = Gtk.Image()
        self.img1_preview.get_style_context().add_class('preview-frame')
        self.img1_preview.set_size_request(200, 120)
        slot1_box.pack_start(self.img1_preview, False, False, 0)

        s1_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_choose1 = Gtk.Button(label="📁 Pilih File...")
        btn_choose1.get_style_context().add_class('btn-choose')
        btn_choose1.connect('clicked', lambda b: self.on_choose_photo(1))
        s1_btn_box.pack_start(btn_choose1, True, True, 0)

        btn_clear1 = Gtk.Button(label="✕ Hapus")
        btn_clear1.get_style_context().add_class('btn-remove')
        btn_clear1.connect('clicked', lambda b: self.on_clear_photo(1))
        s1_btn_box.pack_start(btn_clear1, False, False, 0)
        slot1_box.pack_start(s1_btn_box, False, False, 0)

        self.lbl_path1 = Gtk.Label(label="Belum ada foto")
        self.lbl_path1.get_style_context().add_class('header-desc')
        self.lbl_path1.set_xalign(0.0)
        slot1_box.pack_start(self.lbl_path1, False, False, 0)

        photos_row.pack_start(slot1_box, True, True, 0)

        # === SLOT 2 ===
        slot2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        s2_lbl = Gtk.Label(label="📷 Foto 2 (Opsional):")
        s2_lbl.get_style_context().add_class('section-label')
        s2_lbl.set_xalign(0.0)
        slot2_box.pack_start(s2_lbl, False, False, 0)

        self.img2_preview = Gtk.Image()
        self.img2_preview.get_style_context().add_class('preview-frame')
        self.img2_preview.set_size_request(200, 120)
        slot2_box.pack_start(self.img2_preview, False, False, 0)

        s2_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_choose2 = Gtk.Button(label="📁 Pilih File...")
        btn_choose2.get_style_context().add_class('btn-choose')
        btn_choose2.connect('clicked', lambda b: self.on_choose_photo(2))
        s2_btn_box.pack_start(btn_choose2, True, True, 0)

        btn_clear2 = Gtk.Button(label="✕ Hapus")
        btn_clear2.get_style_context().add_class('btn-remove')
        btn_clear2.connect('clicked', lambda b: self.on_clear_photo(2))
        s2_btn_box.pack_start(btn_clear2, False, False, 0)
        slot2_box.pack_start(s2_btn_box, False, False, 0)

        self.lbl_path2 = Gtk.Label(label="Kosong (Hanya 1 foto)")
        self.lbl_path2.get_style_context().add_class('header-desc')
        self.lbl_path2.set_xalign(0.0)
        slot2_box.pack_start(self.lbl_path2, False, False, 0)

        photos_row.pack_start(slot2_box, True, True, 0)
        main_box.pack_start(photos_row, False, False, 0)

        # Dynamic layout explanation info pill
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info_box.get_style_context().add_class('info-pill')
        info_lbl1 = Gtk.Label(label="✨ Layout Otomatis Dinamis:")
        info_lbl1.set_xalign(0.0)
        info_lbl1.get_style_context().add_class('section-label')
        info_box.pack_start(info_lbl1, False, False, 0)

        info_lbl2 = Gtk.Label(label="• Jika hanya 1 foto: Foto akan ditampilkan terpusat di tengah secara proporsional.\n• Jika 2 foto diisi: Widget otomatis membagi kartu menjadi 2 foto berdampingan (kiri & kanan).")
        info_lbl2.set_xalign(0.0)
        info_lbl2.get_style_context().add_class('header-desc')
        info_box.pack_start(info_lbl2, False, False, 0)
        main_box.pack_start(info_box, False, False, 0)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)

        btn_cancel = Gtk.Button(label="Batal")
        btn_cancel.get_style_context().add_class('btn-cancel')
        btn_cancel.connect('clicked', lambda b: self.destroy())
        btn_box.pack_start(btn_cancel, False, False, 0)

        btn_save = Gtk.Button(label="💾 Simpan & Terapkan")
        btn_save.get_style_context().add_class('btn-save')
        btn_save.connect('clicked', self.on_save)
        btn_box.pack_start(btn_save, False, False, 0)

        main_box.pack_start(btn_box, False, False, 0)

        # Refresh initial thumbnails
        self.update_thumbnails()

    def update_thumbnails(self):
        if self.photo1_path and os.path.exists(self.photo1_path):
            try:
                pb1 = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.photo1_path, 200, 120, True)
                self.img1_preview.set_from_pixbuf(pb1)
                self.lbl_path1.set_text(os.path.basename(self.photo1_path))
            except Exception:
                self.lbl_path1.set_text("Gagal memuat gambar")
        else:
            self.img1_preview.clear()
            self.lbl_path1.set_text("Belum ada foto")

        if self.photo2_path and os.path.exists(self.photo2_path):
            try:
                pb2 = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.photo2_path, 200, 120, True)
                self.img2_preview.set_from_pixbuf(pb2)
                self.lbl_path2.set_text(os.path.basename(self.photo2_path))
            except Exception:
                self.lbl_path2.set_text("Gagal memuat gambar")
        else:
            self.img2_preview.clear()
            self.lbl_path2.set_text("Kosong (Hanya 1 foto aktif)")

    def on_choose_photo(self, slot_num):
        dialog = Gtk.FileChooserDialog(
            title=f"Pilih Foto {slot_num}",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        filter_img = Gtk.FileFilter()
        filter_img.set_name("Gambar (*.jpg, *.png, *.webp)")
        filter_img.add_mime_type("image/jpeg")
        filter_img.add_mime_type("image/png")
        filter_img.add_mime_type("image/webp")
        filter_img.add_pattern("*.jpg")
        filter_img.add_pattern("*.jpeg")
        filter_img.add_pattern("*.png")
        filter_img.add_pattern("*.webp")
        dialog.add_filter(filter_img)

        pictures_dir = os.path.expanduser('~/Pictures')
        if os.path.exists(pictures_dir):
            dialog.set_current_folder(pictures_dir)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if filename and os.path.exists(filename):
                if slot_num == 1:
                    self.photo1_path = filename
                else:
                    self.photo2_path = filename
                self.update_thumbnails()
        dialog.destroy()

    def on_clear_photo(self, slot_num):
        if slot_num == 1:
            self.photo1_path = None
        else:
            self.photo2_path = None
        self.update_thumbnails()

    def on_save(self, widget):
        new_title = self.title_entry.get_text().strip() or "HUGENGSETO"

        # 1. Save Title
        with open(TITLE_FILE, 'w') as f:
            f.write(new_title + "\n")

        # 2. Save Photos
        dest1 = PHOTO1_FILE
        dest2 = PHOTO2_FILE

        saved_p1 = None
        saved_p2 = None

        if self.photo1_path and os.path.exists(self.photo1_path):
            if os.path.abspath(self.photo1_path) != os.path.abspath(dest1):
                try:
                    shutil.copyfile(self.photo1_path, dest1)
                except Exception as e:
                    print("Error copying photo 1:", e)
            saved_p1 = dest1
        else:
            if os.path.exists(dest1):
                try:
                    os.remove(dest1)
                except Exception:
                    pass

        if self.photo2_path and os.path.exists(self.photo2_path):
            if os.path.abspath(self.photo2_path) != os.path.abspath(dest2):
                try:
                    shutil.copyfile(self.photo2_path, dest2)
                except Exception as e:
                    print("Error copying photo 2:", e)
            saved_p2 = dest2
        else:
            if os.path.exists(dest2):
                try:
                    os.remove(dest2)
                except Exception:
                    pass

        data = {
            "title": new_title,
            "photo_1": saved_p1,
            "photo_2": saved_p2,
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        # Notify user
        try:
            p_count = (1 if saved_p1 else 0) + (1 if saved_p2 else 0)
            subprocess.Popen([
                'notify-send',
                '-i', 'preferences-desktop-wallpaper',
                '✨ HUD Berhasil Diperbarui!',
                f'Judul: {new_title} • {p_count} Foto Aktif\nWidget desktop telah diperbarui.'
            ])
        except Exception:
            pass

        # Trigger HUD update immediately
        try:
            subprocess.Popen(['python3', HUD_SCRIPT, '--once'])
        except Exception:
            pass

        self.destroy()

def main():
    win = ChangePhotoDialog()
    win.connect('destroy', Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()
