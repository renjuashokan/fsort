#!/bin/bash
set -e

# Check if version argument is provided
if [ "$1" != "" ]; then
  PKG_VERSION="$1"
else
  PKG_VERSION="1.0.0"
fi

PKG_ARCH="all"

# Create outputs directory if it doesn't exist
OUTPUT_DIR="outputs"
mkdir -p "${OUTPUT_DIR}"

echo "Building FaceSort Debian package..."
echo "Version: $PKG_VERSION"
echo "Architecture: $PKG_ARCH"

# Build the frontend first (Vite production build)
echo "Building React frontend..."
if [ -d "ui" ]; then
    (cd ui && npm run build)
else
    echo "Error: ui directory not found"
    exit 1
fi

# Set package details
PKG_NAME="fsort"
PKG_DIR="${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}"
STAGING_DIR="build_deb_temp/${PKG_DIR}"
CONTROL_FILE="${STAGING_DIR}/DEBIAN/control"
CONTROL_TMP="${STAGING_DIR}/DEBIAN/control.tmp"

# Clean up previous staging
rm -rf "build_deb_temp"
mkdir -p "${STAGING_DIR}"

echo "Creating package structure in ${STAGING_DIR}..."

# Create directory structure
mkdir -p "${STAGING_DIR}/DEBIAN"
mkdir -p "${STAGING_DIR}/opt/fsort"
mkdir -p "${STAGING_DIR}/lib/systemd/system"
mkdir -p "${STAGING_DIR}/var/lib/fsort/cache"
mkdir -p "${STAGING_DIR}/var/lib/fsort/sorted"

# Copy Debian control files
if [ -d "debian" ]; then
    cp -r debian/* "${STAGING_DIR}/DEBIAN/"
    # Remove fsort.service from DEBIAN if it was copied there (it belongs in systemd)
    rm -f "${STAGING_DIR}/DEBIAN/fsort.service"
else
    echo "Error: debian directory not found!"
    exit 1
fi

# Process control file to replace version
sed "s/Version: .*/Version: ${PKG_VERSION}/" "$CONTROL_FILE" > "$CONTROL_TMP" || true
if [ -f "$CONTROL_TMP" ]; then
    mv "$CONTROL_TMP" "$CONTROL_FILE"
else
    # If version line wasn't in template, add it
    sed -i.bak "2i\\
Version: ${PKG_VERSION}" "$CONTROL_FILE" 2>/dev/null || sed -i "" "2i\\
Version: ${PKG_VERSION}
" "$CONTROL_FILE"
    rm -f "${CONTROL_FILE}.bak"
fi

# Ensure there is a newline at the end of the control file
echo "" >> "$CONTROL_FILE"

# Copy service file
echo "Copying service file..."
if [ -f "debian/fsort.service" ]; then
    cp debian/fsort.service "${STAGING_DIR}/lib/systemd/system/"
else
    echo "Error: debian/fsort.service not found"
    exit 1
fi

# Copy python package files & frontend build output
echo "Copying source files..."
cp -r fsort "${STAGING_DIR}/opt/fsort/"
cp -r ui "${STAGING_DIR}/opt/fsort/"
cp pyproject.toml "${STAGING_DIR}/opt/fsort/"
cp -f LICENSE "${STAGING_DIR}/opt/fsort/" 2>/dev/null || true
cp -f README.md "${STAGING_DIR}/opt/fsort/" 2>/dev/null || true

# Set permissions for packaging scripts
chmod 755 "${STAGING_DIR}/DEBIAN/postinst"
chmod 755 "${STAGING_DIR}/DEBIAN/postrm"

# Calculate installed size
INSTALLED_SIZE=$(du -sk "${STAGING_DIR}" | cut -f1)
echo "Installed-Size: ${INSTALLED_SIZE}" >> "$CONTROL_FILE"

# Build the package
echo "Building .deb package..."
if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --root-owner-group --build "${STAGING_DIR}"
    mv "build_deb_temp/${PKG_DIR}.deb" "${OUTPUT_DIR}/"
    echo "Package built successfully: ${OUTPUT_DIR}/${PKG_DIR}.deb"
else
    echo "Warning: dpkg-deb not found. Staging folder structure is ready at ${STAGING_DIR}."
    echo "You can transfer this staging folder to a Debian/Raspberry Pi device and build it using: dpkg-deb --build ${STAGING_DIR}"
fi
