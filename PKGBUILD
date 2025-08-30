# Maintainer: Canmi21 <9997200@qq.com>
# Contributor: Canmi (Canmi21)

pkgname=cursor-free-vip-git
pkgver=1.9.05
pkgrel=1
pkgdesc="Reset Cursor AI MachineID & Auto Sign Up / In & Bypass Higher Token Limit"
arch=('x86_64')
url="https://github.com/yeongpin/cursor-free-vip"
license=('MIT' 'Attribution-NonCommercial-NoDerivatives 4.0 International')
depends=('python' 'cursor-bin' 'chromium' 'nss' 'gtk3' 'libxss' 'libxtst' 'dbus' 'libnotify' 'ttf-liberation' 'noto-fonts')
makedepends=('git' 'python' 'pyinstaller' 'uv' 'chromedriver')
provides=('cursor-free-vip')
source=("cursor-free-vip::git+https://github.com/yeongpin/cursor-free-vip.git" "https://raw.githubusercontent.com/canmi21/openjlc/refs/heads/main/LICENSE")
sha256sums=('SKIP' 'SKIP')

pkgver() {
  cd "$srcdir/cursor-free-vip"
  git describe --tags --always | sed 's/^v//;s/-/./g'
}

build() {
  cd "$srcdir/cursor-free-vip"
  uv venv .venv
  source .venv/bin/activate
  uv pip install -r requirements.txt
  # Ensure DrissionPage chromium dependencies are met on Arch
  python - <<'EOF'
import shutil, sys
for cmd in ['chromium', 'google-chrome-stable', 'google-chrome']:
    if shutil.which(cmd):
        print('browser-ok:', cmd)
        sys.exit(0)
print('warning: no chromium/chrome found in PATH, runtime may fail', file=sys.stderr)
EOF
  pyinstaller --clean --noconfirm --onefile main.py --name cursor-free-vip
}

package() {
  install -Dm644 "$srcdir/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/mit_license"
  install -Dm644 "$srcdir/cursor-free-vip/LICENSE.md" "$pkgdir/usr/share/licenses/$pkgname/attribution_non_commercial_no_derivatives_license"
  install -Dm755 "$srcdir/cursor-free-vip/dist/cursor-free-vip" "$pkgdir/usr/bin/cursor-free-vip"
}