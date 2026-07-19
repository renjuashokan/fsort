#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# build-pkg.sh — Build an Arch Linux package (.pkg.tar.zst) for fsort
# Usage: ./build-pkg.sh [VERSION] [PKGREL]
# Example: ./build-pkg.sh 0.1.1
#          ./build-pkg.sh 0.1.1 2   (bump pkgrel without changing version)
#
# Installation strategy:
#   We pre-build a fsort .whl AND download ALL runtime dependency wheels
#   at build time.  Everything is bundled into the package so that
#   post_install can run a fully offline `pip install --no-index`.
#   This means the target machine never needs PyPI access.
# ---------------------------------------------------------------------------

# ---- Version ---------------------------------------------------------------
if [ "$1" != "" ]; then
    PKG_VERSION="$1"
else
    PKG_VERSION=$(grep -m1 '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    if [ -z "$PKG_VERSION" ]; then
        PKG_VERSION="1.0.0"
    fi
fi

PKGREL="${2:-1}"

OUTPUT_DIR="outputs"
mkdir -p "${OUTPUT_DIR}"

echo "Building fsort Arch package..."
echo "Version : ${PKG_VERSION}"
echo "pkgrel  : ${PKGREL}"

# ---- Build React frontend --------------------------------------------------
echo "Building React frontend..."
if [ -d "ui" ]; then
    [ -d "ui/dist" ] && rm -rf ui/dist
    (cd ui && npm install && npm run build)
else
    echo "Error: ui directory not found"
    exit 1
fi

# ---- Pre-build the fsort wheel ---------------------------------------------
WHEEL_STAGING="build_pkg_wheel_tmp"
rm -rf "${WHEEL_STAGING}"
mkdir -p "${WHEEL_STAGING}"

echo "Pre-building fsort wheel..."
pip wheel . --no-deps --wheel-dir "${WHEEL_STAGING}" --quiet
FSORT_WHEEL=$(ls "${WHEEL_STAGING}"/fsort-*.whl | head -1)
echo "Built: $(basename "${FSORT_WHEEL}")"

# ---- Download all runtime dependency wheels --------------------------------
# These are bundled into the package so post_install can `pip install --no-index`.
DEPS_STAGING="build_pkg_temp_wheels"
rm -rf "${DEPS_STAGING}"
mkdir -p "${DEPS_STAGING}"

echo "Downloading all Python runtime dependencies as wheels..."
pip download \
    --dest "${DEPS_STAGING}" \
    --only-binary=:all: \
    "${FSORT_WHEEL}" 2>&1
echo "Downloaded $(ls "${DEPS_STAGING}" | wc -l) wheel(s) into ${DEPS_STAGING}/"

# ---- Prepare build staging area --------------------------------------------
BUILD_DIR="build_pkg_temp"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# Copy PKGBUILD and install hook
cp arch/PKGBUILD      "${BUILD_DIR}/PKGBUILD"
cp arch/fsort.install "${BUILD_DIR}/fsort.install"

# Inject the correct version and pkgrel into the staged PKGBUILD
sed -i "s/^pkgver=.*/pkgver=${PKG_VERSION}/" "${BUILD_DIR}/PKGBUILD"
sed -i "s/^pkgrel=.*/pkgrel=${PKGREL}/"      "${BUILD_DIR}/PKGBUILD"

# Copy source files that package() will pick up from $srcdir
SRCDIR="${BUILD_DIR}/src"
mkdir -p "${SRCDIR}"

cp -r fsort            "${SRCDIR}/"
cp -r ui               "${SRCDIR}/"
cp    pyproject.toml   "${SRCDIR}/"
cp -f LICENSE          "${SRCDIR}/" 2>/dev/null || true
cp -f README.md        "${SRCDIR}/" 2>/dev/null || true
cp    debian/fsort.service "${SRCDIR}/"

# Copy the pre-built wheel and dependency wheels
cp "${FSORT_WHEEL}" "${SRCDIR}/"
mkdir -p "${SRCDIR}/wheels"
cp "${DEPS_STAGING}"/*.whl "${SRCDIR}/wheels/" 2>/dev/null || true
cp "${DEPS_STAGING}"/*.tar.gz "${SRCDIR}/wheels/" 2>/dev/null || true
cp "${DEPS_STAGING}"/*.zip "${SRCDIR}/wheels/" 2>/dev/null || true
echo "Bundled $(ls "${SRCDIR}/wheels/" | wc -l) dependency artifact(s)"
rm -rf "${WHEEL_STAGING}" "${DEPS_STAGING}"

# Patch staged pyproject.toml version to match the package version
sed -i "s/^version = .*/version = \"${PKG_VERSION}\"/" "${SRCDIR}/pyproject.toml"
echo "Patched staged pyproject.toml version → ${PKG_VERSION}"

# ---- Run makepkg -----------------------------------------------------------
echo "Running makepkg..."
(
    cd "${BUILD_DIR}"
    # --nodeps   : skip dependency check (we trust the dev env)
    # --noextract: sources are pre-populated in src/ — skip extract step
    SRCDEST="$(pwd)/src" makepkg --nodeps --noextract --nocheck 2>&1
)

# ---- Move output -----------------------------------------------------------
PKG_FILE=$(ls "${BUILD_DIR}"/*.pkg.tar.zst 2>/dev/null | head -1)
if [ -n "${PKG_FILE}" ]; then
    mv "${PKG_FILE}" "${OUTPUT_DIR}/"
    BASENAME=$(basename "${PKG_FILE}")
    echo ""
    echo "✓ Package built successfully: ${OUTPUT_DIR}/${BASENAME}"
    echo ""
    echo "Install with:"
    echo "  sudo pacman -U ${OUTPUT_DIR}/${BASENAME}"
else
    echo ""
    echo "Warning: makepkg did not produce a .pkg.tar.zst file."
    echo "Staged sources are in ${BUILD_DIR}/ — you can inspect them and run:"
    echo "  cd ${BUILD_DIR} && makepkg"
fi
