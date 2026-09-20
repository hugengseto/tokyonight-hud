#!/usr/bin/env bash
# ==============================================================================
# Tokyonight Desktop HUD - Clean Uninstaller
# ==============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${RED}${BOLD}Uninstalling Tokyonight Desktop HUD...${NC}\n"

# 1. Stop and disable systemd service
if systemctl --user is-active --quiet tokyonight-hud.service 2>/dev/null; then
    echo "Stopping background service..."
    systemctl --user stop tokyonight-hud.service || true
fi

if systemctl --user is-enabled --quiet tokyonight-hud.service 2>/dev/null; then
    echo "Disabling service..."
    systemctl --user disable tokyonight-hud.service || true
fi

# Remove systemd unit
rm -f "$HOME/.config/systemd/user/tokyonight-hud.service"
systemctl --user daemon-reload || true

# 2. Restore Original Wallpaper if base exists
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/tokyonight-hud"
ORIGINAL_BG=""
if [ -f "$CONFIG_DIR/wallpaper_base.jpg" ]; then
    ORIGINAL_BG="$CONFIG_DIR/wallpaper_base.jpg"
elif [ -f "$CONFIG_DIR/wallpaper_base.png" ]; then
    ORIGINAL_BG="$CONFIG_DIR/wallpaper_base.png"
elif [ -f "$HOME/.config/background.original" ]; then
    ORIGINAL_BG="$HOME/.config/background.original"
fi

if [ -n "$ORIGINAL_BG" ] && command -v gsettings &>/dev/null; then
    echo "Restoring wallpaper to: $ORIGINAL_BG"
    gsettings set org.gnome.desktop.background picture-uri "file://$ORIGINAL_BG" || true
    gsettings set org.gnome.desktop.background picture-uri-dark "file://$ORIGINAL_BG" || true
fi

# 3. Remove application binaries, desktop entries & icons
echo "Removing application binaries and desktop launchers..."
rm -f "$HOME/.local/bin/tokyonight-hud"
rm -f "$HOME/.local/share/applications/tokyonight-hud.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/tokyonight-hud.svg"
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/tokyonight-hud"
rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/tokyonight-hud"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" &>/dev/null || true
fi

# 4. Optional removal of user configs
read -p "Do you want to delete your custom photos, quotes, and goals (~/.config/tokyonight-hud)? [y/N]: " REMOVE_CONF
if [[ "$REMOVE_CONF" =~ ^[Yy]$ ]]; then
    rm -rf "$CONFIG_DIR"
    echo "Configuration directory removed."
else
    echo "Configuration preserved in $CONFIG_DIR."
fi

echo -e "\n${GREEN}${BOLD}✓ Tokyonight Desktop HUD has been completely uninstalled.${NC}\n"
