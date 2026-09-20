#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import time

def get_dir_size(path):
    total = 0
    if not os.path.exists(path):
        return 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except Exception:
                pass
    return total

def run_cleanup():
    bytes_freed = 0

    # 1. Measure and clean thumbnails cache
    thumb_path = os.path.expanduser('~/.cache/thumbnails')
    if os.path.exists(thumb_path):
        size_thumb = get_dir_size(thumb_path)
        for item in os.listdir(thumb_path):
            ipath = os.path.join(thumb_path, item)
            try:
                if os.path.isdir(ipath):
                    shutil.rmtree(ipath, ignore_errors=True)
                else:
                    os.remove(ipath)
            except Exception:
                pass
        bytes_freed += size_thumb

    # 2. Measure and clean user package / dnf caches
    for cdir in ['~/.cache/PackageKit', '~/.cache/dnf5', '~/.cache/pip', '~/.cache/yarn']:
        p = os.path.expanduser(cdir)
        if os.path.exists(p):
            s = get_dir_size(p)
            try:
                shutil.rmtree(p, ignore_errors=True)
                bytes_freed += s
            except Exception:
                pass

    # 3. Clean user journal logs older than 2 days
    try:
        subprocess.run(['journalctl', '--user', '--vacuum-time=2d'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except Exception:
        pass

    # 4. Clean unused flatpak runtimes if available
    if shutil.which('flatpak'):
        try:
            subprocess.run(['flatpak', 'uninstall', '--unused', '-y'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except Exception:
            pass

    # 5. Empty trash if user has files in trash
    trash_files_dir = os.path.expanduser('~/.local/share/Trash/files')
    if os.path.exists(trash_files_dir):
        trash_size = get_dir_size(trash_files_dir)
        try:
            subprocess.run(['gio', 'trash', '--empty'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            bytes_freed += trash_size
        except Exception:
            pass

    # Format freed size
    if bytes_freed >= 1024 * 1024 * 1024:
        freed_str = f"{bytes_freed / (1024 * 1024 * 1024):.2f} GB"
    elif bytes_freed >= 1024 * 1024:
        freed_str = f"{bytes_freed / (1024 * 1024):.1f} MB"
    elif bytes_freed >= 1024:
        freed_str = f"{bytes_freed / 1024:.0f} KB"
    else:
        freed_str = "Cleaned & Optimized"

    # Send desktop notification
    try:
        subprocess.run([
            'notify-send',
            '-a', 'Tokyonight System Cleaner',
            '🧹 System Cleanup Completed',
            f'Freed {freed_str} of junk cache, logs & temporary data.\nStorage & memory refreshed!',
            '-i', 'edit-clear-all',
            '-t', '5000'
        ])
    except Exception:
        pass

    # Trigger HUD wallpaper update
    hud_script = os.path.join(os.path.expanduser('~/.local/share/tokyonight-hud'), 'tokyonight_hud.py')
    if os.path.exists(hud_script):
        subprocess.run(['python3', hud_script, '--once'])

if __name__ == '__main__':
    run_cleanup()
