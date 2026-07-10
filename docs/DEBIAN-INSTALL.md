# Installing FaceSort using Debian package

This document provides instructions for installing FaceSort using the Debian package (.deb).

## Prerequisites

- Debian-based Linux distribution (Debian 12+, Ubuntu 22.04+, Raspberry Pi OS, etc.)
- Python 3.11 or newer with `venv` and `pip` support
- System libraries required by FaceSort:

  ```bash
  sudo apt update
  sudo apt install python3 python3-venv python3-pip ffmpeg libgl1 libglib2.0-0
  ```

  > **Note for Ubuntu 24.04+ / Debian 13+**: `libgl1-mesa-glx` has been replaced by
  > `libgl1`. If `apt` reports `libgl1-mesa-glx` unavailable, use `libgl1` instead (already
  > reflected in the command above).

  > **Note on FFmpeg**: On some Ubuntu releases, `ffmpeg` may report unmet dependencies
  > due to the system's apt sources. Try `sudo apt --fix-broken install` first if this
  > happens, or ensure your system's package index is up to date with `sudo apt update`.

## Installation

1. Download the appropriate .deb package:
   - `fsort_*_all.deb` (Architecture: all)

2. Install prerequisites and then the package:
   ```bash
   sudo apt update
   sudo apt install python3 python3-venv python3-pip ffmpeg libgl1 libglib2.0-0
   sudo dpkg -i fsort_*.deb
   ```

3. If `dpkg` reports unresolved dependencies after step 2, run:
   ```bash
   sudo apt --fix-broken install
   ```


## Post-Installation

After installation, the FaceSort service will be automatically enabled and started.

- **Web Interface**: Access at `http://<your-server-ip>:9876`
- **Default Cache Directory**: `/var/lib/fsort/cache`
- **Default Output Directory**: `/var/lib/fsort/sorted`
- **Default Port**: `9876`
- **Service Name**: `fsort.service`
- **CLI command**: `face-sort` (available system-wide via `/usr/local/bin/face-sort`)

  > **If `face-sort: command not found`** after installing an older `.deb`, the symlink was
  > not created automatically. Add it manually:
  > ```bash
  > sudo ln -sf /opt/fsort/.venv/bin/face-sort /usr/local/bin/face-sort
  > ```
  > Rebuilding and reinstalling the latest `.deb` will also fix this permanently.

To verify the service is running:
```bash
sudo systemctl status fsort.service
```

To find your server's IP address:
```bash
hostname -I
```

## Configuration

FaceSort can be configured by editing the systemd service variables or by editing the configuration file.

### Editing Service Configuration via systemd Override

You can customize the directories, port, host, and configuration file path by overriding the systemd environment variables:

1. Edit the systemd service file:
   ```bash
   sudo systemctl edit fsort.service
   ```

2. Add your custom configurations inside the `[Service]` block:
   ```ini
   [Service]
   Environment=FSORT_PORT=8080
   Environment=FSORT_OUTPUT=/path/to/your/sorted/media
   Environment=FSORT_CACHE=/path/to/your/cache
   Environment=FSORT_HOST=127.0.0.1
   Environment=FSORT_CONFIG=/opt/fsort/config.yaml
   Environment=FSORT_HDD_ROOT=/mnt/sda1
   ```

3. Restart the service to apply changes:
   ```bash
   sudo systemctl restart fsort.service
   ```

### Changing FaceSort Application Settings

You can edit `/opt/fsort/config.yaml` to adjust model settings, match thresholds, and processing parameters:
```bash
sudo nano /opt/fsort/config.yaml
```

Restart the service after editing the config file:
```bash
sudo systemctl restart fsort.service
```

## Service Management

- Check service status:
  ```bash
  sudo systemctl status fsort.service
  ```

- Stop the service:
  ```bash
  sudo systemctl stop fsort.service
  ```

- Start the service:
  ```bash
  sudo systemctl start fsort.service
  ```

- Disable automatic startup:
  ```bash
  sudo systemctl disable fsort.service
  ```

- View logs:
  ```bash
  sudo journalctl -u fsort.service
  ```

## Uninstallation

To remove FaceSort while preserving user data (your cache and sorted media):

```bash
sudo systemctl stop fsort.service
sudo apt remove fsort
```

To completely remove FaceSort including all data, cache, sorted media, and configuration:

```bash
sudo systemctl stop fsort.service
sudo apt remove --purge fsort
```

**Warning:** Using `--purge` will permanently delete the cache and sorted folders in `/var/lib/fsort/` along with all their contents. Use with caution!
