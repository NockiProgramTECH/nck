#!/usr/bin/env sh
# Installateur NCK pour Linux et macOS — aucun Python requis.
#   curl -fsSL https://raw.githubusercontent.com/NockiProgramTECH/nck/main/installateur/installer.sh | sh
# Variables : NCK_VERSION (défaut : dernière), NCK_PREFIX (défaut : ~/.nck), NCK_BIN (défaut : ~/.local/bin)
set -e
DEPOT="NockiProgramTECH/nck"
PREFIX="${NCK_PREFIX:-$HOME/.nck}"
BIN="${NCK_BIN:-$HOME/.local/bin}"

case "$(uname -s)" in
  Linux)  SYS=linux ;;
  Darwin) SYS=macos ;;
  *) echo "Système non pris en charge : $(uname -s). Utilisez : pip install git+https://github.com/$DEPOT" ; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) ARCH=x64 ;;
  arm64|aarch64) ARCH=arm64 ;;
  *) echo "Architecture non prise en charge : $(uname -m)" ; exit 1 ;;
esac

if [ -z "$NCK_VERSION" ]; then
  NCK_VERSION=$(curl -fsSL "https://api.github.com/repos/$DEPOT/releases/latest" | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | head -1)
  [ -n "$NCK_VERSION" ] || { echo "Impossible de déterminer la dernière version (dépôt privé ou hors ligne ?)."; exit 1; }
fi
ARCHIVE="nck-$NCK_VERSION-$SYS-$ARCH.tar.gz"
URL="https://github.com/$DEPOT/releases/download/v$NCK_VERSION/$ARCHIVE"

echo "→ Téléchargement de NCK $NCK_VERSION ($SYS-$ARCH)…"
TMP=$(mktemp -d)
curl -fsSL "$URL" -o "$TMP/$ARCHIVE" || { echo "Téléchargement impossible : $URL"; exit 1; }
rm -rf "$PREFIX"
mkdir -p "$PREFIX" "$BIN"
tar -xzf "$TMP/$ARCHIVE" -C "$PREFIX" --strip-components=1
rm -rf "$TMP"
ln -sf "$PREFIX/nck" "$BIN/nck"
chmod +x "$PREFIX/nck"

# Extension VS Code (si VS Code est présent)
if [ -d "$HOME/.vscode" ] && [ -d "$PREFIX/editeurs/vscode" ]; then
  rm -rf "$HOME/.vscode/extensions/nck-lang"
  cp -R "$PREFIX/editeurs/vscode" "$HOME/.vscode/extensions/nck-lang"
  echo "→ Extension VS Code installée (redémarrez VS Code)."
fi

# PATH
case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    for RC in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
      [ -f "$RC" ] && ! grep -q "NCK_BIN_PATH" "$RC" && printf '\n# NCK_BIN_PATH\nexport PATH="%s:$PATH"\n' "$BIN" >> "$RC"
    done
    echo "→ $BIN ajouté au PATH (ouvrez un nouveau terminal)."
    ;;
esac

echo
"$PREFIX/nck" info
echo
echo "✓ NCK $NCK_VERSION installé. Essayez :  nck $PREFIX/exemples/bonjour.nck"
