# Installing FaceSort using Debian package

This document provides instructions for installing FaceSort using the Debian package (.deb).

## Prerequisites

- Debian-based Linux distribution (Debian, Ubuntu, Raspberry Pi OS, etc.)
- Python 3 (specifically Python 3.14 or newer)
- FFmpeg and common system library packages:
  ```bash
  sudo apt install ffmpeg libgl1-mesa-glx libglib2.0-0
  ```

## Installation

1. Download the appropriate .deb package:
   - `fsort_*_all.deb` (Architecture: all)

2. Install the package:
   ```bash
   sudo dpkg -i fsort_*.deb
   ```

3. If you encounter any dependency issues, run:
   ```bash
   sudo apt-get install -f
   ```

## Post-Installation

After installation, the FaceSort service will be automatically enabled and started.

- **Web Interface**: Access at `http://<your-server-ip>:9876`
- **Default Cache Directory**: `/var/lib/fsort/cache`
- **Default Output Directory**: `/var/lib/fsort/sorted`
- **Default Port**: `9876`
- **Service Name**: `fsort.service`

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
