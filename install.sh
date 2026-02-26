#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python"

echo "==> Creating virtual environment..."
python3 -m venv "$DIR/.venv"

echo "==> Installing dependencies..."
"$DIR/.venv/bin/pip" install --quiet -r "$DIR/requirements.txt"

echo "==> Installing sesyaz package..."
"$DIR/.venv/bin/pip" install --quiet -e "$DIR"

echo "==> Installing icon..."
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_DIR"
cp "$DIR/logo.png" "$ICON_DIR/sesyaz.png"
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "==> Installing .desktop file..."
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
sed "s|Exec=python3 -m sesyaz|Exec=$PYTHON -m sesyaz|" \
    "$DIR/sesyaz.desktop" > "$DESKTOP_DIR/sesyaz.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo ""
echo "Done! Now configure a KDE Custom Shortcut:"
echo "  System Settings → Shortcuts → Custom Shortcuts → New → Command/URL"
echo "  Command: $PYTHON -m sesyaz"
