#!/usr/bin/env python3
import math
import os
import sys
import shutil
import time
import signal
import subprocess
import re
import json
from datetime import datetime
import cairo
import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Pango, PangoCairo, Gtk, Gdk, Gio, GLib
from PIL import Image, ImageFilter, ImageDraw, ImageOps

APP_DIR = os.path.expanduser('~/.local/share/tokyonight-hud')
CACHE_DIR = os.path.expanduser('~/.cache/tokyonight-hud')
CONFIG_DIR = os.path.expanduser('~/.config/tokyonight-hud')
ORIGINAL_BG = os.path.expanduser('~/.config/background.original')
FALLBACK_BG = os.path.expanduser('~/.config/background')

TARGET_A = os.path.join(CACHE_DIR, 'background_a.jpg')
TARGET_B = os.path.join(CACHE_DIR, 'background_b.jpg')
QUOTES_FILE = os.path.join(CONFIG_DIR, 'quotes.json')
GOAL_FILE = os.path.join(CONFIG_DIR, 'daily_goal.json')
ADD_QUOTE_SCRIPT = os.path.join(APP_DIR, 'add_quote_dialog.py')
EDIT_GOAL_SCRIPT = os.path.join(APP_DIR, 'edit_goal_dialog.py')
CLEAN_SCRIPT = os.path.join(APP_DIR, 'clean_system_junk.py')
TITLE_FILE = os.path.join(CONFIG_DIR, 'hud_title.txt')
PHOTO1_FILE = os.path.join(CONFIG_DIR, 'motivation_photo_1.jpg')
PHOTO2_FILE = os.path.join(CONFIG_DIR, 'motivation_photo_2.jpg')
PHOTOS_JSON_FILE = os.path.join(CONFIG_DIR, 'motivation_photos.json')
CHANGE_PHOTO_SCRIPT = os.path.join(APP_DIR, 'change_photo_dialog.py')

os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# 4K Wallpaper Canvas & Card Layout Coordinates
CARD_W = 1440
CARD_H = 1380
CARD_R = 44
CARD_X = 3840 - CARD_W - 90  # 2310
CARD_Y = (2160 - CARD_H) // 2  # 390 (centered vertically on 2160 canvas)

# Ensure backup of original wallpaper exists
if not os.path.exists(ORIGINAL_BG) and os.path.exists(FALLBACK_BG):
    shutil.copy2(FALLBACK_BG, ORIGINAL_BG)

def get_distro_name():
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                d = {}
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        d[k] = v.strip('"\'')
                name = d.get('NAME', 'Linux')
                ver = d.get('VERSION_ID', '')
                if ver:
                    return f"{name.split()[0]} {ver}"
                return name
    except Exception:
        pass
    return "Linux"

def get_base_wallpaper_path():
    # User custom wallpaper in config
    for ext in ['jpg', 'png', 'jpeg']:
        custom = os.path.join(CONFIG_DIR, f'wallpaper_base.{ext}')
        if os.path.exists(custom):
            return custom

    # System original backup
    if os.path.exists(ORIGINAL_BG):
        return ORIGINAL_BG

    # Bundled asset wallpaper
    bundled = os.path.join(APP_DIR, 'assets', 'wallpaper_default.jpg')
    if os.path.exists(bundled):
        return bundled
    bundled_parent = os.path.join(os.path.dirname(APP_DIR), 'assets', 'wallpaper_default.jpg')
    if os.path.exists(bundled_parent):
        return bundled_parent

    if os.path.exists(FALLBACK_BG):
        return FALLBACK_BG

    return None

CACHED_SSD_MODEL = None

def get_ssd_model():
    global CACHED_SSD_MODEL
    if CACHED_SSD_MODEL is not None:
        return CACHED_SSD_MODEL

    try:
        out = subprocess.check_output(['findmnt', '-no', 'SOURCE', '/home'], text=True).strip()
        dev_path = out.split('[')[0].strip()
        dev_name = os.path.basename(dev_path)
        if 'nvme' in dev_name:
            parent = re.sub(r'p\d+$', '', dev_name)
        else:
            parent = re.sub(r'\d+$', '', dev_name)

        model_path = f'/sys/class/block/{parent}/device/model'
        if os.path.exists(model_path):
            with open(model_path) as f:
                model = f.read().strip()
                if model:
                    if 'nvme' in parent:
                        CACHED_SSD_MODEL = f"{model} • NVMe PCIe"
                    else:
                        CACHED_SSD_MODEL = f"{model} • SSD"
                    return CACHED_SSD_MODEL
    except Exception:
        pass

    CACHED_SSD_MODEL = "NVMe SSD • High Speed Storage"
    return CACHED_SSD_MODEL

CACHED_INSTALL_STATS = None

def get_install_stats():
    global CACHED_INSTALL_STATS
    if CACHED_INSTALL_STATS is not None:
        install_dt = CACHED_INSTALL_STATS['install_dt']
    else:
        install_dt = None
        for path in ['/var/log/installer/syslog', '/var/log/anaconda/anaconda.log', '/var/log/pacman.log', '/etc/machine-id']:
            if os.path.exists(path):
                try:
                    ts = os.stat(path).st_mtime
                    install_dt = datetime.fromtimestamp(ts)
                    break
                except Exception:
                    pass
        if not install_dt:
            try:
                ts = os.stat('/etc').st_ctime
                install_dt = datetime.fromtimestamp(ts)
            except Exception:
                install_dt = datetime.now()

    now = datetime.now()
    delta = now - install_dt
    days = max(1, delta.days)
    months = days // 30
    rem_days = days % 30
    install_str = install_dt.strftime('%d %b %Y')

    CACHED_INSTALL_STATS = {
        'install_dt': install_dt,
        'install_str': install_str,
        'days': days,
        'months': months,
        'rem_days': rem_days
    }
    return CACHED_INSTALL_STATS

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

def get_current_quote():
    if not os.path.exists(QUOTES_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(QUOTES_FILE, 'w') as f:
                json.dump({"active_index": None, "quotes": DEFAULT_QUOTES}, f, indent=2)
        except Exception:
            pass
        return DEFAULT_QUOTES[0]

    try:
        with open(QUOTES_FILE) as f:
            data = json.load(f)
        quotes = data.get('quotes', DEFAULT_QUOTES)
        if not quotes:
            return DEFAULT_QUOTES[0]

        active_idx = data.get('active_index')
        if active_idx is not None and 0 <= active_idx < len(quotes):
            return quotes[active_idx]

        day_of_year = datetime.now().timetuple().tm_yday
        return quotes[day_of_year % len(quotes)]
    except Exception:
        return DEFAULT_QUOTES[0]

def get_daily_goal():
    default_text = "Build clean code, solve core problems & stay focused"
    if not os.path.exists(GOAL_FILE):
        return default_text
    try:
        with open(GOAL_FILE) as f:
            data = json.load(f)
            return data.get('goal', default_text)
    except Exception:
        return default_text

def get_hud_title():
    if os.path.exists(TITLE_FILE):
        try:
            with open(TITLE_FILE) as f:
                t = f.read().strip()
                if t:
                    return t
        except Exception:
            pass
    user = os.environ.get('USER', 'SYSTEM').upper()
    return user if user != 'ROOT' else 'SYSTEM OVERVIEW'

def get_motivation_photos_list():
    p1 = PHOTO1_FILE if os.path.exists(PHOTO1_FILE) else None
    if not p1:
        old_p = os.path.join(CONFIG_DIR, 'motivation_photo.jpg')
        if os.path.exists(old_p):
            p1 = old_p

    p2 = PHOTO2_FILE if os.path.exists(PHOTO2_FILE) else None

    if os.path.exists(PHOTOS_JSON_FILE):
        try:
            with open(PHOTOS_JSON_FILE) as f:
                data = json.load(f)
                custom_p1 = data.get('photo_1')
                custom_p2 = data.get('photo_2')
                if custom_p1 and os.path.exists(custom_p1):
                    p1 = custom_p1
                elif custom_p1 is None and 'photo_1' in data:
                    p1 = None

                if custom_p2 and os.path.exists(custom_p2):
                    p2 = custom_p2
                elif custom_p2 is None and 'photo_2' in data:
                    p2 = None
        except Exception:
            pass

    photos = []
    if p1 and os.path.exists(p1):
        photos.append(p1)
    if p2 and os.path.exists(p2):
        photos.append(p2)
    return photos

def get_button_geometries():
    pad = 18
    cw = 1440 - 2 * pad
    gap = 32
    col_w = (cw - 96 - gap) / 2 # 636
    col1_x = pad + 48 # 66
    col2_x = col1_x + col_w + gap # 734

    sub_h1 = 280
    sub_y1 = pad + 304 # 322

    sub_h2 = 270
    sub_y2 = sub_y1 + sub_h1 + 24 # 626

    sub_w3 = cw - 96
    sub_h3 = 360
    sub_y3 = sub_y2 + sub_h2 + 24 # 920

    # 1. Open Trash button (row 1 left)
    t_bw = 160
    t_bh = 40
    t_by = sub_y1 + 205

    # 2. Clean Junk button (row 1 left)
    c_bw = 166
    c_bh = 40
    c_by = sub_y1 + 205

    c_bx = col1_x + col_w - c_bw - 24 # 512
    t_bx = c_bx - t_bw - 12 # 340

    # 3. Set Goal button (row 2 left)
    g_bw = 130
    g_bh = 36
    g_by = sub_y2 + 14
    g_bx = col1_x + col_w - g_bw - 24 # 548

    # 4. Add Quote button (row 2 right)
    q_bw = 168
    q_bh = 36
    q_by = sub_y2 + 14
    q_bx = col2_x + col_w - q_bw - 24 # 1182

    # 5. Change Photo button (row 3 top right)
    p_bw = 140
    p_bh = 34
    p_by = sub_y3 + 12
    p_bx = col1_x + sub_w3 - p_bw - 16

    return {
        'trash': (t_bx, t_by, t_bw, t_bh),
        'clean': (c_bx, c_by, c_bw, c_bh),
        'goal': (g_bx, g_by, g_bw, g_bh),
        'quote': (q_bx, q_by, q_bw, q_bh),
        'photo': (p_bx, p_by, p_bw, p_bh)
    }

def get_system_stats():
    # Disk /home
    disk_total, disk_used, disk_free = shutil.disk_usage('/home')
    disk_total_gb = disk_total / (1024**3)
    disk_used_gb = disk_used / (1024**3)
    disk_free_gb = disk_free / (1024**3)
    disk_pct = (disk_used / disk_total) * 100.0 if disk_total > 0 else 0

    # SSD Hardware model
    ssd_model = get_ssd_model()

    # Install & Transition stats
    inst = get_install_stats()

    # Developer Mindset Quote
    q_data = get_current_quote()

    # Trash (~/.local/share/Trash)
    trash_files_dir = os.path.expanduser('~/.local/share/Trash/files')
    trash_count = 0
    trash_size = 0
    if os.path.exists(trash_files_dir):
        try:
            with os.scandir(trash_files_dir) as it:
                for entry in it:
                    trash_count += 1
                    try:
                        stat = entry.stat(follow_symlinks=False)
                        if entry.is_file(follow_symlinks=False):
                            trash_size += stat.st_size
                        elif entry.is_dir(follow_symlinks=False):
                            for root, _, files in os.walk(entry.path):
                                for f in files:
                                    try:
                                        trash_size += os.path.getsize(os.path.join(root, f))
                                    except:
                                        pass
                    except:
                        pass
        except Exception:
            pass

    if trash_size >= 1024**3:
        trash_str = f"{trash_size / (1024**3):.1f} GB"
    elif trash_size >= 1024**2:
        trash_str = f"{trash_size / (1024**2):.1f} MB"
    elif trash_size >= 1024:
        trash_str = f"{trash_size / 1024:.1f} KB"
    else:
        trash_str = f"{trash_size} B"

    # RAM (/proc/meminfo)
    mem = {}
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].split()[0])
        ram_total = mem.get('MemTotal', 0) / 1024 / 1024
        ram_avail = mem.get('MemAvailable', 0) / 1024 / 1024
        ram_used = ram_total - ram_avail
        ram_pct = (ram_used / ram_total) * 100.0 if ram_total > 0 else 0
    except:
        ram_total, ram_used, ram_pct = 16.0, 6.0, 37.5

    return {
        'disk_total_gb': disk_total_gb,
        'disk_used_gb': disk_used_gb,
        'disk_free_gb': disk_free_gb,
        'disk_pct': disk_pct,
        'ssd_model': ssd_model,
        'install_str': inst['install_str'],
        'transition_days': inst['days'],
        'transition_months': inst['months'],
        'quote': q_data.get('quote', 'Talk is cheap. Show me the code.'),
        'author': q_data.get('author', 'Linus Torvalds'),
        'goal': get_daily_goal(),
        'trash_count': trash_count,
        'trash_size_str': trash_str,
        'trash_size_bytes': trash_size,
        'ram_total_gb': ram_total,
        'ram_used_gb': ram_used,
        'ram_pct': ram_pct,
        'hud_title': get_hud_title(),
        'distro_name': get_distro_name(),
        'photos': get_motivation_photos_list(),
        'time_str': datetime.now().strftime('%H:%M')
    }

def round_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()

def draw_hud_card(stats, w=1440, h=1380):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surface)
    pango_ctx = PangoCairo.create_context(ctx)
    layout = Pango.Layout(pango_ctx)

    pad = 18
    pad = 18
    cw = w - 2 * pad
    ch = h - 2 * pad
    r = 44

    # 1. Main Card Surface (Tokyo Night Rich Deep Contrast)
    round_rect(ctx, pad, pad, cw, ch, r)
    card_grad = cairo.LinearGradient(pad, pad, pad + cw * 0.7, pad + ch)
    card_grad.add_color_stop_rgba(0.0, 0.10, 0.11, 0.16, 0.98) # #1a1b26
    card_grad.add_color_stop_rgba(0.5, 0.08, 0.09, 0.13, 0.98) # #14151f
    card_grad.add_color_stop_rgba(1.0, 0.05, 0.05, 0.08, 0.99) # #0d0e14
    ctx.set_source(card_grad)
    ctx.fill_preserve()

    # Outer Bevel Border with high specular pop
    bevel_grad = cairo.LinearGradient(pad, pad, pad + cw, pad + ch)
    bevel_grad.add_color_stop_rgba(0.0, 0.49, 0.81, 1.0, 0.95) # Cyan neon
    bevel_grad.add_color_stop_rgba(0.35, 0.48, 0.64, 0.97, 0.75) # Blue neon
    bevel_grad.add_color_stop_rgba(0.70, 0.73, 0.60, 0.97, 0.50) # Purple
    bevel_grad.add_color_stop_rgba(1.0, 0.15, 0.16, 0.25, 0.85)
    ctx.set_source(bevel_grad)
    ctx.set_line_width(3.5)
    ctx.stroke()

    # Top Specular Highlight Line
    ctx.save()
    round_rect(ctx, pad + 3, pad + 3, cw - 6, ch - 6, r - 3)
    ctx.clip()
    highlight_grad = cairo.LinearGradient(pad + 40, pad + 3, pad + cw - 40, pad + 3)
    highlight_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.0)
    highlight_grad.add_color_stop_rgba(0.2, 1.0, 1.0, 1.0, 0.45)
    highlight_grad.add_color_stop_rgba(0.5, 0.85, 0.95, 1.0, 0.75)
    highlight_grad.add_color_stop_rgba(0.8, 1.0, 1.0, 1.0, 0.45)
    highlight_grad.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
    ctx.set_source(highlight_grad)
    ctx.set_line_width(3.0)
    ctx.move_to(pad + 35, pad + 4)
    ctx.line_to(pad + cw - 35, pad + 4)
    ctx.stroke()
    ctx.restore()

    # 2. Header Section
    ctx.save()
    ctx.arc(pad + 52, pad + 60, 22, 0, 2 * math.pi)
    ctx.set_source_rgba(0.49, 0.81, 1.0, 0.35)
    ctx.fill()
    dot_grad = cairo.RadialGradient(pad + 50, pad + 58, 1, pad + 52, pad + 60, 13)
    dot_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0)
    dot_grad.add_color_stop_rgba(0.4, 0.49, 0.81, 1.0, 1.0)
    dot_grad.add_color_stop_rgba(1.0, 0.40, 0.75, 1.0, 1.0)
    ctx.arc(pad + 52, pad + 60, 13, 0, 2 * math.pi)
    ctx.set_source(dot_grad)
    ctx.fill()
    ctx.restore()

    # Title: 28pt Bold - Bright Electric Cyan (Dynamic & Customizable)
    hud_title = stats.get('hud_title', 'HUGENGSETO')
    layout.set_font_description(Pango.FontDescription('Inter Bold 28'))
    layout.set_text(hud_title, -1)
    ctx.set_source_rgba(0.49, 0.81, 1.0, 1.0)
    ctx.move_to(pad + 88, pad + 42)
    PangoCairo.show_layout(ctx, layout)

    # OS / Time Badge: 18pt Bold (Far right)
    badge_time = f"{stats.get('distro_name', 'Linux')} • {stats['time_str']}"
    layout.set_font_description(Pango.FontDescription('Inter Bold 18'))
    layout.set_text(badge_time, -1)
    t_ink, t_log = layout.get_pixel_extents()
    bw1 = t_log.width + 36
    bh1 = 46
    bx1 = pad + cw - bw1 - 44
    by1 = pad + 38

    ctx.save()
    round_rect(ctx, bx1, by1, bw1, bh1, 23)
    pill_grad = cairo.LinearGradient(bx1, by1, bx1, by1 + bh1)
    pill_grad.add_color_stop_rgba(0.0, 0.48, 0.64, 0.97, 0.30)
    pill_grad.add_color_stop_rgba(1.0, 0.48, 0.64, 0.97, 0.12)
    ctx.set_source(pill_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.49, 0.81, 1.0, 0.70)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.set_source_rgba(0.95, 0.97, 1.0, 1.0) # Bright pure white-blue
    ctx.move_to(bx1 + 18, by1 + 11)
    PangoCairo.show_layout(ctx, layout)
    ctx.restore()

    # Linux Transition Journey Badge: 16pt Bold
    badge_journey = f"Linux Transition: {stats['transition_days']} Days • Since {stats['install_str']}"
    layout.set_font_description(Pango.FontDescription('Inter Bold 16'))
    layout.set_text(badge_journey, -1)
    j_ink, j_log = layout.get_pixel_extents()
    bw2 = j_log.width + 36
    bh2 = 46
    bx2 = bx1 - bw2 - 16
    by2 = pad + 38

    ctx.save()
    round_rect(ctx, bx2, by2, bw2, bh2, 23)
    j_grad = cairo.LinearGradient(bx2, by2, bx2, by2 + bh2)
    j_grad.add_color_stop_rgba(0.0, 0.62, 0.81, 0.42, 0.32)
    j_grad.add_color_stop_rgba(1.0, 0.49, 0.81, 1.0, 0.14)
    ctx.set_source(j_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.62, 0.85, 0.45, 0.80)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.set_source_rgba(0.70, 0.98, 0.65, 1.0) # High contrast luminous green
    ctx.move_to(bx2 + 18, by2 + 11)
    PangoCairo.show_layout(ctx, layout)
    ctx.restore()

    # Header Divider Line with 3D groove
    ctx.save()
    ctx.set_source_rgba(0.48, 0.64, 0.97, 0.35)
    ctx.set_line_width(1.8)
    ctx.move_to(pad + 44, pad + 108)
    ctx.line_to(pad + cw - 44, pad + 108)
    ctx.stroke()
    ctx.restore()

    # 3. Storage Section
    layout.set_font_description(Pango.FontDescription('Inter Bold 18'))
    layout.set_text('DISK STORAGE', -1)
    ctx.set_source_rgba(0.70, 0.76, 0.92, 1.0) # Crisp visible light lavender
    ctx.move_to(pad + 48, pad + 128)
    PangoCairo.show_layout(ctx, layout)
    t_ink, t_log = layout.get_pixel_extents()

    # Hardware Pill Badge (Samsung SSD 980 500GB • NVMe PCIe)
    ssd_model_str = stats.get('ssd_model', 'Samsung SSD 980 500GB • NVMe PCIe')
    layout.set_font_description(Pango.FontDescription('Inter Bold 15'))
    layout.set_text(ssd_model_str, -1)
    b_ink, b_log = layout.get_pixel_extents()
    bw = b_log.width + 30
    bh = 32
    bx = pad + 48 + t_log.width + 16
    by = pad + 122

    ctx.save()
    round_rect(ctx, bx, by, bw, bh, 16)
    b_grad = cairo.LinearGradient(bx, by, bx, by + bh)
    b_grad.add_color_stop_rgba(0.0, 0.49, 0.81, 1.0, 0.30)
    b_grad.add_color_stop_rgba(1.0, 0.49, 0.81, 1.0, 0.12)
    ctx.set_source(b_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.49, 0.81, 1.0, 0.75)
    ctx.set_line_width(1.6)
    ctx.stroke()
    ctx.set_source_rgba(0.75, 0.90, 1.0, 1.0) # Bright Ice Cyan
    ctx.move_to(bx + 15, by + 6)
    PangoCairo.show_layout(ctx, layout)
    ctx.restore()

    # Free storage: 46pt Bold
    layout.set_font_description(Pango.FontDescription('Inter Bold 46'))
    free_txt = f"{stats['disk_free_gb']:.0f} GB"
    layout.set_text(free_txt, -1)
    ctx.set_source_rgba(0.49, 0.81, 1.0, 1.0) # Electric cyan
    ctx.move_to(pad + 48, pad + 160)
    PangoCairo.show_layout(ctx, layout)
    ink, logical = layout.get_pixel_extents()

    # Sublabel "Available": 22pt
    layout.set_font_description(Pango.FontDescription('Inter Semi-Bold 22'))
    layout.set_text('Available', -1)
    ctx.set_source_rgba(0.85, 0.90, 1.0, 1.0) # Bright white-lavender
    ctx.move_to(pad + 48 + logical.width + 18, pad + 182)
    PangoCairo.show_layout(ctx, layout)

    # Right side: Used & Total: 20pt Bold
    used_txt = f"{stats['disk_used_gb']:.0f} GB / {stats['disk_total_gb']:.0f} GB Used ({stats['disk_pct']:.0f}%)"
    layout.set_font_description(Pango.FontDescription('Inter Bold 20'))
    layout.set_text(used_txt, -1)
    ink, logical = layout.get_pixel_extents()
    ctx.set_source_rgba(0.75, 0.85, 1.0, 1.0) # Clear high contrast
    ctx.move_to(pad + cw - 48 - logical.width, pad + 182)
    PangoCairo.show_layout(ctx, layout)

    # Progress Bar
    bar_x = pad + 48
    bar_y = pad + 236
    bar_w = cw - 96
    bar_h = 24
    round_rect(ctx, bar_x, bar_y, bar_w, bar_h, 12)
    track_grad = cairo.LinearGradient(bar_x, bar_y, bar_x, bar_y + bar_h)
    track_grad.add_color_stop_rgba(0.0, 0.12, 0.14, 0.22, 1.0) # Visible deep navy
    track_grad.add_color_stop_rgba(1.0, 0.16, 0.18, 0.28, 1.0)
    ctx.set_source(track_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.35, 0.42, 0.65, 0.80) # Visible track border
    ctx.set_line_width(1.6)
    ctx.stroke()

    fill_w = max(24, (bar_w * (stats['disk_pct'] / 100.0)))
    round_rect(ctx, bar_x, bar_y, fill_w, bar_h, 12)
    fill_grad = cairo.LinearGradient(bar_x, bar_y, bar_x + fill_w, bar_y)
    fill_grad.add_color_stop_rgba(0.0, 0.16, 0.76, 0.87, 1.0) # Neon cyan #2ac3de
    fill_grad.add_color_stop_rgba(1.0, 0.48, 0.64, 0.97, 1.0) # Tokyo night blue #7aa2f7
    ctx.set_source(fill_grad)
    ctx.fill_preserve()

    ctx.save()
    round_rect(ctx, bar_x, bar_y, fill_w, bar_h, 12)
    ctx.clip()
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.45)
    ctx.set_line_width(2.4)
    ctx.move_to(bar_x + 8, bar_y + 3)
    ctx.line_to(bar_x + fill_w - 8, bar_y + 3)
    ctx.stroke()
    ctx.restore()

    # Middle Divider
    ctx.save()
    ctx.set_source_rgba(0.48, 0.64, 0.97, 0.28)
    ctx.set_line_width(1.5)
    ctx.move_to(pad + 44, pad + 284)
    ctx.line_to(pad + cw - 44, pad + 284)
    ctx.stroke()
    ctx.restore()

    # 4. 2x2 Grid Subcards setup
    geoms = get_button_geometries()
    t_bx, t_by, t_bw, t_bh = geoms['trash']
    c_bx, c_by, c_bw, c_bh = geoms['clean']
    g_bx, g_by, g_bw, g_bh = geoms['goal']
    q_bx, q_by, q_bw, q_bh = geoms['quote']
    p_bx, p_by, p_bw, p_bh = geoms['photo']

    gap = 32
    col_w = (cw - 96 - gap) / 2
    col1_x = pad + 48
    col2_x = col1_x + col_w + gap

    sub_h1 = 280
    sub_y1 = pad + 304

    sub_h2 = 270
    sub_y2 = sub_y1 + sub_h1 + 24

    def draw_subcard_shell(x, y, w, h, r=24, border_color=(0.49, 0.81, 1.0)):
        round_rect(ctx, x, y + 4, w, h, r)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.55)
        ctx.fill()

        round_rect(ctx, x, y, w, h, r)
        s_grad = cairo.LinearGradient(x, y, x + w, y + h)
        s_grad.add_color_stop_rgba(0.0, 0.15, 0.17, 0.26, 0.98)
        s_grad.add_color_stop_rgba(1.0, 0.10, 0.11, 0.17, 0.98)
        ctx.set_source(s_grad)
        ctx.fill_preserve()

        b_grad = cairo.LinearGradient(x, y, x + w, y + h)
        b_grad.add_color_stop_rgba(0.0, border_color[0], border_color[1], border_color[2], 0.85)
        b_grad.add_color_stop_rgba(0.5, 0.48, 0.64, 0.97, 0.55)
        b_grad.add_color_stop_rgba(1.0, 0.15, 0.16, 0.25, 0.85)
        ctx.set_source(b_grad)
        ctx.set_line_width(2.2)
        ctx.stroke()

        ctx.save()
        round_rect(ctx, x + 2, y + 2, w - 4, h - 4, r - 2)
        ctx.clip()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.20)
        ctx.set_line_width(2.0)
        ctx.move_to(x + 18, y + 3)
        ctx.line_to(x + w - 18, y + 3)
        ctx.stroke()
        ctx.restore()

    # Row 1 Left: TRASH & MAINTENANCE
    draw_subcard_shell(col1_x, sub_y1, col_w, sub_h1, 24, (0.49, 0.81, 1.0))

    layout.set_font_description(Pango.FontDescription('Inter Bold 17'))
    layout.set_text('TRASH & MAINTENANCE', -1)
    ctx.set_source_rgba(0.70, 0.76, 0.92, 1.0)
    ctx.move_to(col1_x + 30, sub_y1 + 24)
    PangoCairo.show_layout(ctx, layout)

    layout.set_font_description(Pango.FontDescription('Inter Bold 40'))
    count_unit = "File" if stats['trash_count'] == 1 else "Files"
    count_txt = f"{stats['trash_count']} {count_unit}"
    layout.set_text(count_txt, -1)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
    ctx.move_to(col1_x + 30, sub_y1 + 62)
    PangoCairo.show_layout(ctx, layout)

    size_txt = f"Size: {stats['trash_size_str']}"
    layout.set_font_description(Pango.FontDescription('Inter Semi-Bold 20'))
    layout.set_text(size_txt, -1)
    ctx.set_source_rgba(1.0, 0.78, 0.40, 1.0)
    ctx.move_to(col1_x + 30, sub_y1 + 130)
    PangoCairo.show_layout(ctx, layout)

    # Clean • Empty badge
    rec_text = "Needs Cleanup" if stats['trash_count'] > 0 else "Clean • Empty"
    layout.set_font_description(Pango.FontDescription('Inter Bold 16'))
    layout.set_text(rec_text, -1)
    ink, logical = layout.get_pixel_extents()
    rw = logical.width + 28
    rh = 40
    rx = col1_x + 30
    ry = sub_y1 + 205

    round_rect(ctx, rx, ry, rw, rh, 20)
    if stats['trash_count'] > 0:
        ctx.set_source_rgba(0.97, 0.46, 0.56, 0.30)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.97, 0.46, 0.56, 0.85)
        ctx.set_line_width(1.8)
        ctx.stroke()
        ctx.set_source_rgba(1.0, 0.60, 0.68, 1.0)
    else:
        ctx.set_source_rgba(0.62, 0.81, 0.42, 0.30)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.62, 0.85, 0.45, 0.85)
        ctx.set_line_width(1.8)
        ctx.stroke()
        ctx.set_source_rgba(0.70, 0.98, 0.65, 1.0)
    ctx.move_to(rx + 14, ry + 10)
    PangoCairo.show_layout(ctx, layout)

    # Draw Open Trash button (Cyan accent)
    layout.set_font_description(Pango.FontDescription('Inter Bold 15'))
    layout.set_text('Open Trash ↗', -1)
    round_rect(ctx, t_bx, t_by, t_bw, t_bh, 20)
    t_grad = cairo.LinearGradient(t_bx, t_by, t_bx, t_by + t_bh)
    t_grad.add_color_stop_rgba(0.0, 0.49, 0.81, 1.0, 0.35)
    t_grad.add_color_stop_rgba(1.0, 0.49, 0.81, 1.0, 0.14)
    ctx.set_source(t_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.49, 0.81, 1.0, 0.85)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.set_source_rgba(0.88, 0.95, 1.0, 1.0)
    ctx.move_to(t_bx + 14, t_by + 10)
    PangoCairo.show_layout(ctx, layout)

    # Draw Clean Junk button (Amber/Orange accent)
    layout.set_text('🧹 Clean Junk', -1)
    round_rect(ctx, c_bx, c_by, c_bw, c_bh, 20)
    c_grad = cairo.LinearGradient(c_bx, c_by, c_bx, c_by + c_bh)
    c_grad.add_color_stop_rgba(0.0, 1.0, 0.62, 0.35, 0.35)
    c_grad.add_color_stop_rgba(1.0, 1.0, 0.45, 0.30, 0.14)
    ctx.set_source(c_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(1.0, 0.65, 0.35, 0.85)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.set_source_rgba(1.0, 0.90, 0.75, 1.0)
    ctx.move_to(c_bx + 14, c_by + 10)
    PangoCairo.show_layout(ctx, layout)

    # Row 1 Right: SYSTEM MEMORY (RAM)
    draw_subcard_shell(col2_x, sub_y1, col_w, sub_h1, 24, (0.73, 0.60, 0.97))

    layout.set_font_description(Pango.FontDescription('Inter Bold 17'))
    layout.set_text('SYSTEM MEMORY (RAM)', -1)
    ctx.set_source_rgba(0.70, 0.76, 0.92, 1.0)
    ctx.move_to(col2_x + 30, sub_y1 + 24)
    PangoCairo.show_layout(ctx, layout)

    layout.set_font_description(Pango.FontDescription('Inter Bold 40'))
    ram_txt = f"{stats['ram_used_gb']:.1f} GB"
    layout.set_text(ram_txt, -1)
    ctx.set_source_rgba(0.85, 0.72, 1.0, 1.0)
    ctx.move_to(col2_x + 30, sub_y1 + 62)
    PangoCairo.show_layout(ctx, layout)
    ink, logical = layout.get_pixel_extents()

    layout.set_font_description(Pango.FontDescription('Inter Semi-Bold 20'))
    layout.set_text(f"/ {stats['ram_total_gb']:.1f} GB ({stats['ram_pct']:.0f}%)", -1)
    ctx.set_source_rgba(0.85, 0.90, 1.0, 1.0)
    ctx.move_to(col2_x + 30 + logical.width + 16, sub_y1 + 78)
    PangoCairo.show_layout(ctx, layout)

    rbar_x = col2_x + 30
    rbar_y = sub_y1 + 138
    rbar_w = col_w - 60
    rbar_h = 20
    round_rect(ctx, rbar_x, rbar_y, rbar_w, rbar_h, 10)
    ctx.set_source(track_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.35, 0.42, 0.65, 0.80)
    ctx.set_line_width(1.6)
    ctx.stroke()

    rfill_w = max(20, (rbar_w * (stats['ram_pct'] / 100.0)))
    round_rect(ctx, rbar_x, rbar_y, rfill_w, rbar_h, 10)
    rbar_grad = cairo.LinearGradient(rbar_x, rbar_y, rbar_x + rfill_w, rbar_y)
    rbar_grad.add_color_stop_rgba(0.0, 0.73, 0.60, 0.97, 1.0)
    rbar_grad.add_color_stop_rgba(1.0, 0.97, 0.46, 0.56, 1.0)
    ctx.set_source(rbar_grad)
    ctx.fill_preserve()

    ctx.save()
    round_rect(ctx, rbar_x, rbar_y, rfill_w, rbar_h, 10)
    ctx.clip()
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.45)
    ctx.set_line_width(2.2)
    ctx.move_to(rbar_x + 6, rbar_y + 3)
    ctx.line_to(rbar_x + rfill_w - 6, rbar_y + 3)
    ctx.stroke()
    ctx.restore()

    layout.set_font_description(Pango.FontDescription('Inter Semi-Bold 18'))
    ram_status = "Optimal & Smooth" if stats['ram_pct'] < 75 else "High Load"
    layout.set_text(f"Status: {ram_status}", -1)
    ctx.set_source_rgba(0.49, 0.81, 1.0, 1.0)
    ctx.move_to(col2_x + 30, sub_y1 + 214)
    PangoCairo.show_layout(ctx, layout)

    # Row 2 Left: 🎯 TODAY'S MAIN FOCUS (Daily Goal)
    draw_subcard_shell(col1_x, sub_y2, col_w, sub_h2, 24, (0.45, 0.85, 0.75))

    layout.set_font_description(Pango.FontDescription('Inter Bold 16'))
    layout.set_text('🎯 TODAY\'S MAIN FOCUS', -1)
    ctx.set_source_rgba(0.45, 0.90, 0.78, 1.0)
    ctx.move_to(col1_x + 28, sub_y2 + 22)
    PangoCairo.show_layout(ctx, layout)

    # Draw Set Goal button (Mint/Emerald accent)
    layout.set_font_description(Pango.FontDescription('Inter Bold 14'))
    layout.set_text('✏️ Set Goal', -1)
    round_rect(ctx, g_bx, g_by, g_bw, g_bh, 18)
    g_grad = cairo.LinearGradient(g_bx, g_by, g_bx, g_by + g_bh)
    g_grad.add_color_stop_rgba(0.0, 0.45, 0.90, 0.78, 0.35)
    g_grad.add_color_stop_rgba(1.0, 0.30, 0.70, 0.60, 0.14)
    ctx.set_source(g_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.45, 0.90, 0.78, 0.90)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
    ctx.move_to(g_bx + 13, g_by + 8)
    PangoCairo.show_layout(ctx, layout)

    # Goal Text
    layout.set_width(Pango.SCALE * (col_w - 56))
    layout.set_wrap(Pango.WrapMode.WORD)
    layout.set_font_description(Pango.FontDescription('Inter Semi-Bold 20'))
    goal_txt = f'“{stats.get("goal", "Build clean code, solve core problems & stay focused")}”'
    layout.set_text(goal_txt, -1)
    ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
    ctx.move_to(col1_x + 28, sub_y2 + 68)
    PangoCairo.show_layout(ctx, layout)

    # Goal badge
    layout.set_width(-1)
    layout.set_font_description(Pango.FontDescription('Inter Bold 14'))
    layout.set_text('ACTIVE SPRINT • PRIORITY #1', -1)
    ink, log_b = layout.get_pixel_extents()
    badge_y = sub_y2 + sub_h2 - 44
    round_rect(ctx, col1_x + 28, badge_y, log_b.width + 24, 30, 15)
    ctx.set_source_rgba(0.45, 0.85, 0.75, 0.22)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.45, 0.85, 0.75, 0.65)
    ctx.set_line_width(1.4)
    ctx.stroke()
    ctx.set_source_rgba(0.65, 0.95, 0.85, 1.0)
    ctx.move_to(col1_x + 40, badge_y + 6)
    PangoCairo.show_layout(ctx, layout)

    # Row 2 Right: 💡 DAILY DEVELOPER MINDSET
    draw_subcard_shell(col2_x, sub_y2, col_w, sub_h2, 24, (0.78, 0.65, 1.0))

    layout.set_font_description(Pango.FontDescription('Inter Bold 16'))
    layout.set_text('💡 DEVELOPER MINDSET', -1)
    ctx.set_source_rgba(0.85, 0.72, 1.0, 1.0)
    ctx.move_to(col2_x + 28, sub_y2 + 22)
    PangoCairo.show_layout(ctx, layout)

    # Draw Add Quote button (Purple accent)
    layout.set_font_description(Pango.FontDescription('Inter Bold 14'))
    layout.set_text('+ Add Quote ✍', -1)
    round_rect(ctx, q_bx, q_by, q_bw, q_bh, 18)
    q_grad = cairo.LinearGradient(q_bx, q_by, q_bx, q_by + q_bh)
    q_grad.add_color_stop_rgba(0.0, 0.78, 0.65, 1.0, 0.40)
    q_grad.add_color_stop_rgba(1.0, 0.49, 0.81, 1.0, 0.18)
    ctx.set_source(q_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.78, 0.65, 1.0, 0.90)
    ctx.set_line_width(1.8)
    ctx.stroke()
    ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
    ctx.move_to(q_bx + 13, q_by + 8)
    PangoCairo.show_layout(ctx, layout)

    # Quote Text
    quote_text = f'“{stats["quote"]}”'
    layout.set_width(Pango.SCALE * (col_w - 56))
    layout.set_wrap(Pango.WrapMode.WORD)
    layout.set_font_description(Pango.FontDescription('Inter Medium Italic 20'))
    layout.set_text(quote_text, -1)
    q_ink, q_log = layout.get_pixel_extents()

    ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
    ctx.move_to(col2_x + 28, sub_y2 + 68)
    PangoCairo.show_layout(ctx, layout)

    # Author attribution
    author_text = f'— {stats["author"]}'
    layout.set_width(-1)
    layout.set_font_description(Pango.FontDescription('Inter Bold 16'))
    layout.set_text(author_text, -1)
    ctx.set_source_rgba(1.0, 0.78, 0.40, 1.0)
    ctx.move_to(col2_x + 28, sub_y2 + 68 + q_log.height + 8)
    PangoCairo.show_layout(ctx, layout)

    # Row 3: 🖼️ DYNAMIC CENTERED PHOTO GALLERY (Max 2 Photos, Proportional & Centered)
    sub_w3 = cw - 96
    sub_h3 = 360
    sub_y3 = sub_y2 + sub_h2 + 24
    draw_subcard_shell(col1_x, sub_y3, sub_w3, sub_h3, 24, (1.0, 0.65, 0.40))

    photos = stats.get('photos', [])
    valid_photos = [p for p in photos if p and os.path.exists(p)]

    pad_inner = 16
    avail_h = sub_h3 - 2 * pad_inner

    def render_photo(img_path, target_x, target_y, target_w, target_h, radius=16, border_color=(1.0, 0.70, 0.40)):
        try:
            raw_im = Image.open(img_path)
            im = ImageOps.exif_transpose(raw_im).convert('RGBA')

            resized = im.resize((target_w, target_h), Image.Resampling.LANCZOS)

            mask = Image.new('L', (target_w, target_h), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.rounded_rectangle([0, 0, target_w, target_h], radius=radius, fill=255)
            resized.putalpha(mask)

            data = bytearray(resized.tobytes('raw', 'BGRA'))
            surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, target_w, target_h)
            ctx.set_source_surface(surf, target_x, target_y)
            ctx.paint()

            # Glowing rounded border around the photo
            round_rect(ctx, target_x, target_y, target_w, target_h, radius)
            ctx.set_source_rgba(border_color[0], border_color[1], border_color[2], 0.85)
            ctx.set_line_width(2.0)
            ctx.stroke()
            return True
        except Exception as e:
            print(f"Error rendering photo {img_path}:", e)
            return False

    if len(valid_photos) >= 2:
        # Load both and calculate natural proportional widths at avail_h
        dims = []
        for p in valid_photos[:2]:
            try:
                raw_im = Image.open(p)
                im = ImageOps.exif_transpose(raw_im)
                asp = im.width / float(im.height)
                pw = max(60, min(500, int(avail_h * asp)))
                dims.append(pw)
            except Exception:
                dims.append(int(avail_h * 0.75))

        gap = 28
        total_photos_w = dims[0] + gap + dims[1]
        start_x = col1_x + int((sub_w3 - total_photos_w) / 2)
        y_pos = sub_y3 + pad_inner

        # Photo 1 (Left)
        render_photo(valid_photos[0], start_x, y_pos, dims[0], avail_h, 16, (1.0, 0.72, 0.42))

        # Photo 2 (Right)
        render_photo(valid_photos[1], start_x + dims[0] + gap, y_pos, dims[1], avail_h, 16, (0.49, 0.81, 1.0))

    elif len(valid_photos) == 1:
        # 1 Photo: Centered in the card at natural aspect ratio
        try:
            raw_im = Image.open(valid_photos[0])
            im = ImageOps.exif_transpose(raw_im)
            asp = im.width / float(im.height)
            pw = max(60, min(700, int(avail_h * asp)))
        except Exception:
            pw = int(avail_h * 0.75)

        start_x = col1_x + int((sub_w3 - pw) / 2)
        y_pos = sub_y3 + pad_inner
        render_photo(valid_photos[0], start_x, y_pos, pw, avail_h, 18, (1.0, 0.72, 0.42))

    else:
        # No photos placeholder
        layout.set_font_description(Pango.FontDescription('Inter Bold 18'))
        layout.set_text("📷 Belum ada foto terpasang\nKlik 'Kelola Foto' untuk menambahkan foto", -1)
        layout.set_alignment(Pango.Alignment.CENTER)
        ink, log = layout.get_pixel_extents()
        ctx.set_source_rgba(0.75, 0.82, 0.96, 0.7)
        ctx.move_to(col1_x + (sub_w3 - log.width) / 2, sub_y3 + (sub_h3 - log.height) / 2)
        PangoCairo.show_layout(ctx, layout)
        layout.set_alignment(Pango.Alignment.LEFT)

    # Floating "📷 Kelola Foto" button at top-right
    p_bx, p_by, p_bw, p_bh = geoms['photo']
    layout.set_width(-1)
    layout.set_font_description(Pango.FontDescription('Inter Bold 13'))
    layout.set_text('📷 Kelola Foto', -1)
    round_rect(ctx, p_bx, p_by, p_bw, p_bh, 16)
    p_grad = cairo.LinearGradient(p_bx, p_by, p_bx, p_by + p_bh)
    p_grad.add_color_stop_rgba(0.0, 0.12, 0.14, 0.22, 0.85)
    p_grad.add_color_stop_rgba(1.0, 0.08, 0.09, 0.15, 0.92)
    ctx.set_source(p_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(1.0, 0.65, 0.40, 0.85)
    ctx.set_line_width(1.6)
    ctx.stroke()
    ctx.set_source_rgba(1.0, 0.85, 0.65, 1.0)
    ctx.move_to(p_bx + 14, p_by + 8)
    PangoCairo.show_layout(ctx, layout)

    # 6. Bottom Milestone Footer - Centered Capsule Badge
    custom_footer = None
    footer_file = os.path.join(CONFIG_DIR, 'hud_footer.txt')
    if os.path.exists(footer_file):
        try:
            with open(footer_file) as f:
                c = f.read().strip()
                if c:
                    custom_footer = c
        except Exception:
            pass

    if custom_footer:
        footer_txt = custom_footer
    else:
        distro_tag = stats.get('distro_name', 'LINUX').upper()
        footer_txt = f"{distro_tag} RUNTIME: {stats['transition_days']} DAYS ({stats['transition_months']} MONTHS) • INSTALLED {stats['install_str'].upper()}"
    layout.set_font_description(Pango.FontDescription('Inter Bold 15'))
    layout.set_text(footer_txt, -1)
    ink, logical = layout.get_pixel_extents()

    fb_w = logical.width + 40
    fb_h = 36
    fb_x = pad + (cw - fb_w) / 2
    fb_y = pad + ch - 44

    ctx.save()
    round_rect(ctx, fb_x, fb_y, fb_w, fb_h, 18)
    fb_grad = cairo.LinearGradient(fb_x, fb_y, fb_x, fb_y + fb_h)
    fb_grad.add_color_stop_rgba(0.0, 0.48, 0.64, 0.97, 0.28)
    fb_grad.add_color_stop_rgba(1.0, 0.48, 0.64, 0.97, 0.10)
    ctx.set_source(fb_grad)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.48, 0.64, 0.97, 0.60)
    ctx.set_line_width(1.4)
    ctx.stroke()
    ctx.set_source_rgba(0.75, 0.88, 1.0, 1.0)
    ctx.move_to(fb_x + 20, fb_y + 8)
    PangoCairo.show_layout(ctx, layout)
    ctx.restore()

    card_png_path = os.path.join(CACHE_DIR, 'hud_card.png')
    tmp_path = os.path.join(CACHE_DIR, f'hud_card_tmp_{os.getpid()}.png')
    surface.write_to_png(tmp_path)
    os.replace(tmp_path, card_png_path)
    return card_png_path

class FastCompositor:
    def __init__(self):
        self.card_w = CARD_W
        self.card_h = CARD_H
        self.card_r = CARD_R
        self.card_x = CARD_X
        self.card_y = CARD_Y
        self.base_image = None
        self._init_base()

    def _init_base(self):
        base_file = get_base_wallpaper_path()
        base = Image.open(base_file).convert('RGBA')

        s_margin = 80
        sw, sh = self.card_w + 2 * s_margin, self.card_h + 2 * s_margin

        s_amb = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
        d_amb = ImageDraw.Draw(s_amb)
        d_amb.rounded_rectangle(
            [s_margin + 18, s_margin + 18 + 24, s_margin + self.card_w - 18, s_margin + self.card_h - 18 + 24],
            radius=self.card_r,
            fill=(0, 0, 0, 160)
        )
        s_amb = s_amb.filter(ImageFilter.GaussianBlur(radius=40))

        s_dir = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
        d_dir = ImageDraw.Draw(s_dir)
        d_dir.rounded_rectangle(
            [s_margin + 18, s_margin + 18 + 12, s_margin + self.card_w - 18, s_margin + self.card_h - 18 + 12],
            radius=self.card_r,
            fill=(0, 0, 0, 200)
        )
        s_dir = s_dir.filter(ImageFilter.GaussianBlur(radius=16))

        shadow = Image.alpha_composite(s_amb, s_dir)
        base.alpha_composite(shadow, (self.card_x - s_margin, self.card_y - s_margin))

        mask = Image.new('L', (self.card_w, self.card_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([18, 18, self.card_w - 18, self.card_h - 18], radius=self.card_r, fill=255)

        backdrop = base.crop((self.card_x, self.card_y, self.card_x + self.card_w, self.card_y + self.card_h))
        blurred = backdrop.filter(ImageFilter.GaussianBlur(radius=20))
        base.paste(blurred, (self.card_x, self.card_y), mask=mask)

        self.base_image = base

    def composite_and_save(self, card_png_path, target_path):
        card = Image.open(card_png_path).convert('RGBA')
        out = self.base_image.copy()
        out.alpha_composite(card, (self.card_x, self.card_y))
        out.convert('RGB').save(target_path, quality=94)

compositor = None

def get_compositor():
    global compositor
    if compositor is None:
        compositor = FastCompositor()
    return compositor

def update_wallpaper(stats, target_path):
    card_file = draw_hud_card(stats)
    comp = get_compositor()
    comp.composite_and_save(card_file, target_path)

def set_gnome_background(file_path):
    uri = f"file://{os.path.abspath(file_path)}"
    os.system(f"gsettings set org.gnome.desktop.background picture-uri '{uri}'")
    os.system(f"gsettings set org.gnome.desktop.background picture-uri-dark '{uri}'")

def run_once():
    stats = get_system_stats()
    target = TARGET_A
    update_wallpaper(stats, target)
    set_gnome_background(target)
    print(f"[{stats['time_str']}] HUD updated successfully! Quote='{stats['quote'][:30]}...'")

class RealtimeHUDDaemon:
    def __init__(self):
        self.active_target = TARGET_A
        self.last_signature = None
        self.debounce_source = None
        self.monitors = []
        self.overlay_windows = []
        self.screen_handler_id = None

    def get_signature(self, stats):
        ram_bucket = round(stats['ram_used_gb'] * 2) / 2
        photos_tuple = tuple(stats.get('photos', []))
        photos_mtime = tuple(os.path.getmtime(p) for p in stats.get('photos', []) if os.path.exists(p))
        return (
            round(stats['disk_free_gb'], 1),
            round(stats['disk_used_gb'], 1),
            stats['trash_count'],
            stats['trash_size_bytes'],
            ram_bucket,
            stats['time_str'],
            stats.get('quote', ''),
            stats.get('hud_title', ''),
            photos_tuple,
            photos_mtime
        )

    def refresh(self, force=False):
        try:
            stats = get_system_stats()
            sig = self.get_signature(stats)
            if force or sig != self.last_signature:
                next_target = TARGET_B if self.active_target == TARGET_A else TARGET_A
                t0 = time.time()
                update_wallpaper(stats, next_target)
                set_gnome_background(next_target)
                dt = (time.time() - t0) * 1000
                self.active_target = next_target
                self.last_signature = sig
                print(f"[{stats['time_str']}] Realtime Update ({dt:.0f}ms): Quote='{stats['quote'][:25]}...', Disk={stats['disk_free_gb']:.0f}GB, RAM={stats['ram_used_gb']:.1f}GB", flush=True)
        except Exception as e:
            print("Error in refresh:", e, file=sys.stderr, flush=True)

    def on_trash_changed(self, monitor, file, other_file, event_type):
        if self.debounce_source is not None:
            GLib.source_remove(self.debounce_source)
        self.debounce_source = GLib.timeout_add(150, self._debounced_trash_refresh)

    def _debounced_trash_refresh(self):
        self.debounce_source = None
        self.refresh(force=True)
        return False

    def on_periodic_tick(self):
        self.refresh(force=False)
        return True

    def destroy_overlay_windows(self):
        for win in self.overlay_windows:
            try:
                win.destroy()
            except Exception:
                pass
        self.overlay_windows = []

    def on_monitors_changed(self, screen):
        print("Display monitors configuration changed, re-initializing overlays...", flush=True)
        self.init_overlay_windows()

    def init_overlay_windows(self):
        self.destroy_overlay_windows()
        try:
            display = Gdk.Display.get_default()
            if not display:
                print("No GDK display available for desktop overlay", file=sys.stderr)
                return

            screen = display.get_default_screen()
            if self.screen_handler_id is None:
                self.screen_handler_id = screen.connect('monitors-changed', self.on_monitors_changed)

            # 4K Canvas geometry:
            card_x, card_y = CARD_X, CARD_Y
            card_w, card_h = CARD_W, CARD_H

            geoms = get_button_geometries()

            n_monitors = display.get_n_monitors()
            print(f"Initializing desktop interactive precision overlays for {n_monitors} monitor(s)...", flush=True)

            for i in range(n_monitors):
                m = display.get_monitor(i)
                geom = m.get_geometry()
                mon_w = geom.width
                mon_h = geom.height
                mon_x = geom.x
                mon_y = geom.y

                scale = max(mon_w / 3840.0, mon_h / 2160.0)
                offset_x = (mon_w - 3840.0 * scale) / 2.0
                offset_y = (mon_h - 2160.0 * scale) / 2.0

                win_x = mon_x + int(round(offset_x + card_x * scale))
                win_y = mon_y + int(round(offset_y + card_y * scale))
                win_w = int(round(card_w * scale))
                win_h = int(round(card_h * scale))

                win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
                win.get_style_context().add_class(f'overlay-win-{i}')
                win.set_title(f'Tokyonight HUD Overlay Mon{i}')
                win.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
                win.set_skip_taskbar_hint(True)
                win.set_skip_pager_hint(True)
                win.set_accept_focus(False)
                win.set_decorated(False)
                win.set_keep_below(True)

                visual = screen.get_rgba_visual()
                if visual:
                    win.set_visual(visual)
                win.set_app_paintable(True)
                win.move(win_x, win_y)
                win.resize(win_w, win_h)

                fixed = Gtk.Fixed()
                win.add(fixed)

                # 1. Trash Button (Row 1 Left)
                t_bx = int(round((card_x + geoms['trash'][0]) * scale)) - int(round(card_x * scale))
                t_by = int(round((card_y + geoms['trash'][1]) * scale)) - int(round(card_y * scale))
                t_bw = int(round(geoms['trash'][2] * scale))
                t_bh = int(round(geoms['trash'][3] * scale))

                # 2. Clean Junk Button (Row 1 Left)
                c_bx = int(round((card_x + geoms['clean'][0]) * scale)) - int(round(card_x * scale))
                c_by = int(round((card_y + geoms['clean'][1]) * scale)) - int(round(card_y * scale))
                c_bw = int(round(geoms['clean'][2] * scale))
                c_bh = int(round(geoms['clean'][3] * scale))

                # 3. Set Goal Button (Row 2 Left)
                g_bx = int(round((card_x + geoms['goal'][0]) * scale)) - int(round(card_x * scale))
                g_by = int(round((card_y + geoms['goal'][1]) * scale)) - int(round(card_y * scale))
                g_bw = int(round(geoms['goal'][2] * scale))
                g_bh = int(round(geoms['goal'][3] * scale))

                # 4. Add Quote Button (Row 2 Right)
                q_bx = int(round((card_x + geoms['quote'][0]) * scale)) - int(round(card_x * scale))
                q_by = int(round((card_y + geoms['quote'][1]) * scale)) - int(round(card_y * scale))
                q_bw = int(round(geoms['quote'][2] * scale))
                q_bh = int(round(geoms['quote'][3] * scale))

                # 5. Change Photo Button (Row 3 Right)
                p_bx = int(round((card_x + geoms['photo'][0]) * scale)) - int(round(card_x * scale))
                p_by = int(round((card_y + geoms['photo'][1]) * scale)) - int(round(card_y * scale))
                p_bw = int(round(geoms['photo'][2] * scale))
                p_bh = int(round(geoms['photo'][3] * scale))

                # Create Buttons
                btn_trash = Gtk.Button()
                btn_trash.set_name(f'btn-trash-{i}')
                btn_trash.set_size_request(t_bw, t_bh)
                fixed.put(btn_trash, t_bx, t_by)

                btn_clean = Gtk.Button()
                btn_clean.set_name(f'btn-clean-{i}')
                btn_clean.set_size_request(c_bw, c_bh)
                fixed.put(btn_clean, c_bx, c_by)

                btn_goal = Gtk.Button()
                btn_goal.set_name(f'btn-goal-{i}')
                btn_goal.set_size_request(g_bw, g_bh)
                fixed.put(btn_goal, g_bx, g_by)

                btn_quote = Gtk.Button()
                btn_quote.set_name(f'btn-quote-{i}')
                btn_quote.set_size_request(q_bw, q_bh)
                fixed.put(btn_quote, q_bx, q_by)

                btn_photo = Gtk.Button()
                btn_photo.set_name(f'btn-photo-{i}')
                btn_photo.set_size_request(p_bw, p_bh)
                fixed.put(btn_photo, p_bx, p_by)

                # Cursor pointer
                def on_cursor(widget, *args):
                    w = widget.get_window()
                    if w:
                        cursor = Gdk.Cursor.new_from_name(display, 'pointer')
                        w.set_cursor(cursor)

                for btn in [btn_trash, btn_clean, btn_goal, btn_quote, btn_photo]:
                    btn.connect('realize', on_cursor)
                    btn.connect('enter-notify-event', on_cursor)

                btn_trash.connect('clicked', lambda b: subprocess.Popen(['gio', 'open', 'trash:///']))
                btn_clean.connect('clicked', lambda b: subprocess.Popen(['python3', CLEAN_SCRIPT]))
                btn_goal.connect('clicked', lambda b: subprocess.Popen(['python3', EDIT_GOAL_SCRIPT]))
                btn_quote.connect('clicked', lambda b: subprocess.Popen(['python3', ADD_QUOTE_SCRIPT]))
                btn_photo.connect('clicked', lambda b: subprocess.Popen(['python3', CHANGE_PHOTO_SCRIPT]))

                # CSS Provider for precise, beautiful hover glow
                css_provider = Gtk.CssProvider()
                css_data = f"""
                .overlay-win-{i} {{
                    background-color: transparent;
                }}
                .overlay-win-{i} button {{
                    min-width: 0;
                    min-height: 0;
                    padding: 0;
                    margin: 0;
                    border: 1.5px solid transparent;
                    border-radius: 9999px;
                    background: transparent;
                    box-shadow: none;
                    transition: all 180ms cubic-bezier(0.4, 0, 0.2, 1);
                }}
                #btn-trash-{i}:hover {{
                    background-color: rgba(125, 207, 255, 0.25);
                    border: 1.5px solid #7dcfff;
                    border-radius: 9999px;
                    box-shadow: 0 0 10px rgba(125, 207, 255, 0.45);
                }}
                #btn-trash-{i}:active {{
                    background-color: rgba(125, 207, 255, 0.40);
                }}
                #btn-clean-{i}:hover {{
                    background-color: rgba(255, 177, 89, 0.25);
                    border: 1.5px solid #ffb159;
                    border-radius: 9999px;
                    box-shadow: 0 0 10px rgba(255, 177, 89, 0.45);
                }}
                #btn-clean-{i}:active {{
                    background-color: rgba(255, 177, 89, 0.40);
                }}
                #btn-goal-{i}:hover {{
                    background-color: rgba(115, 218, 202, 0.25);
                    border: 1.5px solid #73daca;
                    border-radius: 9999px;
                    box-shadow: 0 0 10px rgba(115, 218, 202, 0.45);
                }}
                #btn-goal-{i}:active {{
                    background-color: rgba(115, 218, 202, 0.40);
                }}
                #btn-quote-{i}:hover {{
                    background-color: rgba(187, 154, 247, 0.25);
                    border: 1.5px solid #bb9af7;
                    border-radius: 9999px;
                    box-shadow: 0 0 10px rgba(187, 154, 247, 0.45);
                }}
                #btn-quote-{i}:active {{
                    background-color: rgba(187, 154, 247, 0.40);
                }}
                #btn-photo-{i}:hover {{
                    background-color: rgba(255, 158, 100, 0.25);
                    border: 1.5px solid #ff9e64;
                    border-radius: 9999px;
                    box-shadow: 0 0 10px rgba(255, 158, 100, 0.45);
                }}
                #btn-photo-{i}:active {{
                    background-color: rgba(255, 158, 100, 0.40);
                }}
                """.encode('utf-8')
                css_provider.load_from_data(css_data)
                Gtk.StyleContext.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

                win.show_all()

                # Constrain input shape so ONLY buttons catch mouse events
                gdk_win = win.get_window()
                if gdk_win:
                    reg = cairo.Region(cairo.RectangleInt(t_bx, t_by, t_bw, t_bh))
                    reg.union(cairo.RectangleInt(c_bx, c_by, c_bw, c_bh))
                    reg.union(cairo.RectangleInt(g_bx, g_by, g_bw, g_bh))
                    reg.union(cairo.RectangleInt(q_bx, q_by, q_bw, q_bh))
                    reg.union(cairo.RectangleInt(p_bx, p_by, p_bw, p_bh))
                    gdk_win.input_shape_combine_region(reg, 0, 0)

                self.overlay_windows.append(win)
                model_name = m.get_model() or f"Monitor-{i}"
                print(f"  -> Monitor {i} ({model_name}): Win=({win_x},{win_y}) [{win_w}x{win_h}], Trash=({t_bx},{t_by}) [{t_bw}x{t_bh}], Clean=({c_bx},{c_by}) [{c_bw}x{c_bh}], Goal=({g_bx},{g_by}) [{g_bw}x{g_bh}], Quote=({q_bx},{q_by}) [{q_bw}x{q_bh}], Photo=({p_bx},{p_by}) [{p_bw}x{p_bh}]", flush=True)

        except Exception as e:
            print("Failed to initialize desktop interactive overlay windows:", e, file=sys.stderr, flush=True)

    def start(self):
        print("Starting Tokyonight Realtime Inotify HUD Daemon...", flush=True)

        get_compositor()
        self.refresh(force=True)
        self.init_overlay_windows()

        trash_base = os.path.expanduser('~/.local/share/Trash')
        trash_files = os.path.join(trash_base, 'files')
        trash_info = os.path.join(trash_base, 'info')

        for path in [trash_files, trash_info, trash_base]:
            os.makedirs(path, exist_ok=True)
            gfile = Gio.File.new_for_path(path)
            mon = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
            mon.connect('changed', self.on_trash_changed)
            self.monitors.append(mon)
            print(f"  -> Monitoring {path} via inotify", flush=True)

        # Also monitor quotes.json for changes
        if os.path.exists(QUOTES_FILE):
            g_qfile = Gio.File.new_for_path(QUOTES_FILE)
            mon_q = g_qfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            mon_q.connect('changed', lambda m, f, of, et: self.refresh(force=True))
            self.monitors.append(mon_q)
            print(f"  -> Monitoring {QUOTES_FILE} for quote updates", flush=True)

        # Also monitor daily_goal.json for changes
        if os.path.exists(GOAL_FILE):
            g_gfile = Gio.File.new_for_path(GOAL_FILE)
            mon_g = g_gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            mon_g.connect('changed', lambda m, f, of, et: self.refresh(force=True))
            self.monitors.append(mon_g)
            print(f"  -> Monitoring {GOAL_FILE} for goal updates", flush=True)

        # Monitor hud_title.txt for title updates
        if os.path.exists(TITLE_FILE):
            g_tfile = Gio.File.new_for_path(TITLE_FILE)
            mon_t = g_tfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            mon_t.connect('changed', lambda m, f, of, et: self.refresh(force=True))
            self.monitors.append(mon_t)
            print(f"  -> Monitoring {TITLE_FILE} for title updates", flush=True)

        # Monitor motivation_photos.json and photo files
        for p_watch in [PHOTOS_JSON_FILE, PHOTO1_FILE, PHOTO2_FILE]:
            if os.path.exists(p_watch):
                g_p = Gio.File.new_for_path(p_watch)
                mon_p = g_p.monitor_file(Gio.FileMonitorFlags.NONE, None)
                mon_p.connect('changed', lambda m, f, of, et: self.refresh(force=True))
                self.monitors.append(mon_p)
                print(f"  -> Monitoring {p_watch} for photo updates", flush=True)

        # Periodic tick for clock/stats (inotify handles instant file/trash/quote/goal changes)
        GLib.timeout_add_seconds(15, self.on_periodic_tick)

        signal.signal(signal.SIGINT, lambda s, f: GLib.idle_add(self.stop))
        signal.signal(signal.SIGTERM, lambda s, f: GLib.idle_add(self.stop))

        Gtk.main()

    def stop(self):
        print("\nStopping Tokyonight HUD Daemon...", flush=True)
        self.destroy_overlay_windows()
        Gtk.main_quit()
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            run_once()
        elif sys.argv[1] == '--daemon':
            daemon = RealtimeHUDDaemon()
            daemon.start()
        elif sys.argv[1] == '--restore':
            if os.path.exists(ORIGINAL_BG):
                set_gnome_background(ORIGINAL_BG)
                print("Restored original wallpaper.")
            else:
                print("No original wallpaper found.")
        else:
            print("Usage: tokyonight_hud.py [--daemon | --once | --restore]")
    else:
        run_once()
