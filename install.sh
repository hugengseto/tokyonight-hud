#!/usr/bin/env bash
# ==============================================================================
# Tokyonight Desktop HUD - Universal Linux Installer
# Supported: Fedora, Ubuntu, Debian, Arch Linux, openSUSE
# ==============================================================================

set -e

CYAN='\033[0;36m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
cat << "EOF"
  _____ _____ _  ____   ______  _   _ _____ _____ _    _ _______ 
 |_   _/ ____| |/ /\ \ / / __ \| \ | |_   _/ ____| |  | |__   __|
   | || |    | ' /  \ V / |  | |  \| | | || |  __ | |__| |  | |   
   | || |    |  <    > <| |  | | . ` | | || | |_ ||  __  |  | |   
  _| || |____| . \  / . \ |__| | |\  |_| || |__| || |  | |  | |   
 |_____\_____|_|\_\/_/ \_\____/|_| \_|_____\_____||_|  |_|  |_|   
                     DESKTOP SYSTEM HUD
EOF
echo -e "${BLUE}★ Modern, Interactive Tokyo Night Desktop HUD for Linux ★${NC}\n"

# 1. Detect Package Manager and Install Dependencies
echo -e "${CYAN}[1/5] Checking system dependencies...${NC}"

install_deps() {
    if command -v dnf &>/dev/null; then
        echo "Detected Fedora / RHEL (dnf). Installing packages..."
        sudo dnf install -y python3-gobject python3-cairo python3-pillow trash-cli libnotify
    elif command -v apt-get &>/dev/null; then
        echo "Detected Debian / Ubuntu (apt). Installing packages..."
        sudo apt-get update
        sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-cairo python3-pil trash-cli libnotify-bin
    elif command -v pacman &>/dev/null; then
        echo "Detected Arch Linux (pacman). Installing packages..."
        sudo pacman -S --needed --noconfirm python-gobject python-cairo python-pillow trash-cli libnotify gtk3
    elif command -v zypper &>/dev/null; then
        echo "Detected openSUSE (zypper). Installing packages..."
        sudo zypper install -y python3-gobject python3-cairo python3-Pillow trash-cli libnotify-tools
    else
        echo -e "${YELLOW}Warning: Unknown package manager. Please ensure Python3, PyGObject, Cairo, Pillow, and trash-cli are installed.${NC}"
    fi
}

# Check if required python packages can be imported
if ! python3 -c "import gi, cairo, PIL" &>/dev/null; then
    echo -e "${YELLOW}Missing Python dependencies. Running package manager installer...${NC}"
    install_deps
else
    echo -e "${GREEN}✓ Core Python libraries (PyGObject, Cairo, Pillow) are ready.${NC}"
fi

# 2. Directory Setup
echo -e "${CYAN}[2/5] Creating application directories...${NC}"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/tokyonight-hud"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/tokyonight-hud"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/tokyonight-hud"
BIN_DIR="$HOME/.local/bin"
APP_DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$CACHE_DIR" "$BIN_DIR" "$APP_DESKTOP_DIR" "$ICON_DIR" "$SYSTEMD_USER_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 3. Copy Application Files
echo -e "${CYAN}[3/5] Installing application files...${NC}"
cp -r "$SCRIPT_DIR/src/"* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR"/*.py

# Copy Assets
mkdir -p "$INSTALL_DIR/assets"
if [ -d "$SCRIPT_DIR/assets" ]; then
    cp -r "$SCRIPT_DIR/assets/"* "$INSTALL_DIR/assets/"
fi

# Install CLI wrapper
cp "$SCRIPT_DIR/bin/tokyonight-hud" "$BIN_DIR/tokyonight-hud"
chmod +x "$BIN_DIR/tokyonight-hud"

# Install Desktop Entry & Icon
cp "$SCRIPT_DIR/packaging/tokyonight-hud.desktop" "$APP_DESKTOP_DIR/tokyonight-hud.desktop"
if [ -f "$SCRIPT_DIR/assets/tokyonight-hud.svg" ]; then
    cp "$SCRIPT_DIR/assets/tokyonight-hud.svg" "$ICON_DIR/tokyonight-hud.svg"
fi

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APP_DESKTOP_DIR" &>/dev/null || true
fi

# Detect & Backup Current Wallpaper if needed
if [ ! -f "$CONFIG_DIR/wallpaper_base.jpg" ] && [ ! -f "$CONFIG_DIR/wallpaper_base.png" ]; then
    if command -v gsettings &>/dev/null; then
        CURRENT_BG=$(gsettings get org.gnome.desktop.background picture-uri | tr -d "'" | sed 's|file://||')
        if [ -n "$CURRENT_BG" ] && [ -f "$CURRENT_BG" ] && [[ "$CURRENT_BG" != *"tokyonight-hud"* ]]; then
            echo "Backing up current wallpaper as base: $CURRENT_BG"
            cp "$CURRENT_BG" "$CONFIG_DIR/wallpaper_base.jpg"
        elif [ -f "$SCRIPT_DIR/assets/wallpaper_default.jpg" ]; then
            echo "Setting default Tokyo Night wallpaper base..."
            cp "$SCRIPT_DIR/assets/wallpaper_default.jpg" "$CONFIG_DIR/wallpaper_base.jpg"
        fi
    elif [ -f "$SCRIPT_DIR/assets/wallpaper_default.jpg" ]; then
        cp "$SCRIPT_DIR/assets/wallpaper_default.jpg" "$CONFIG_DIR/wallpaper_base.jpg"
    fi
fi

# Default title if not configured
if [ ! -f "$CONFIG_DIR/hud_title.txt" ]; then
    DEFAULT_TITLE="${USER^^}"
    [ "$DEFAULT_TITLE" == "ROOT" ] && DEFAULT_TITLE="SYSTEM OVERVIEW"
    echo "$DEFAULT_TITLE" > "$CONFIG_DIR/hud_title.txt"
fi

# 4. Systemd User Service Setup
echo -e "${CYAN}[4/5] Configuring systemd background service...${NC}"
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE 2>/dev/null || true
cp "$SCRIPT_DIR/packaging/tokyonight-hud.service" "$SYSTEMD_USER_DIR/tokyonight-hud.service"
systemctl --user daemon-reload
systemctl --user enable tokyonight-hud.service
systemctl --user restart tokyonight-hud.service

# 5. Initial Render
echo -e "${CYAN}[5/5] Generating initial HUD render...${NC}"
python3 "$INSTALL_DIR/tokyonight_hud.py" --once || true

echo -e "\n${GREEN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✓ TOKYONIGHT DESKTOP HUD INSTALLED SUCCESSFULLY!          ${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════════════════${NC}\n"

echo -e "${BOLD}Quick Usage:${NC}"
echo -e "  • ${CYAN}tokyonight-hud settings${NC}  : Open full Settings Control Center (GUI)"
echo -e "  • ${CYAN}tokyonight-hud photo${NC}     : Change motivation photos"
echo -e "  • ${CYAN}tokyonight-hud goal${NC}      : Update daily sprint focus"
echo -e "  • ${CYAN}tokyonight-hud quote${NC}     : Add a developer quote"
echo -e "  • ${CYAN}tokyonight-hud clean${NC}     : Run safe cache/junk cleaner"
echo -e "  • ${CYAN}tokyonight-hud status${NC}    : Check daemon status"
echo -e "  • ${CYAN}tokyonight-hud reload${NC}    : Force immediate wallpaper refresh\n"

# Verify PATH for ~/.local/bin
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "${YELLOW}Note: Add ~/.local/bin to your PATH to run 'tokyonight-hud' from anywhere:${NC}"
    echo -e "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc\n"
fi
