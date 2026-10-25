# Discord Activity Overlay

A small activity-only extension for [Discover Overlay](https://github.com/trigg/Discover) on Linux. It keeps the screen quiet until someone speaks, joins, or leaves a Discord voice channel.

## Behavior

- Names and avatars appear while speaking and hide two seconds after speech stops.
- Join and leave labels last five seconds.
- Switching channels clears old labels; your own normal departure stays quiet.
- When Discord reports a voice disconnect after a connected state, a delayed connection-loss notice appears if you are still assigned to that channel. This is a best-effort signal, not a network monitor; complete Discord/process shutdowns may prevent the notice.
- Compact circular avatars at 40% opacity, transparent name backgrounds, white names, and green speaking rings.
- A local 40-person demo uses random groups of 1–5 speakers.
- Active speakers sort first, then the most recent speakers.
- A compact one-row placement box defaults to roughly 410 × 52 pixels on a 2560 × 1440 monitor. Its size scales with monitor resolution. Top alignment prevents content clipping after resizing; additional participants wrap into columns and can exceed a very small box.
- An optional combined launcher starts native Discord with the overlay and closes the overlay when Discord exits. Closing Discord to the tray keeps both running.
- On KDE Wayland, an optional **Shift + ` (~)** shortcut opens placement mode. Drag the box, resize its edges, then press the shortcut again or click the green area to save.

The extension patches Discover Overlay in memory. It does not modify Discord or the installed Discover package.

## Requirements

- Linux desktop with working Discover Overlay. Tested on CachyOS, KDE Plasma, Wayland, with Discover Overlay Flatpak 0.7.10 (its runtime reports 0.7.9).
- Native Discord desktop app, signed in. Discover must be authorized through Discord.
- Python 3 for the installer and Flatpak for the runtime.

Other desktop environments and future Discover versions are unverified. This extension uses Discover's internal Python interfaces, which may change.

## Install

Install [Discover Overlay from Flathub](https://flathub.org/apps/io.github.trigg.discover_overlay):

```sh
flatpak install flathub io.github.trigg.discover_overlay
python3 install.py --monitor DP-3 --combined --move-hotkey --autostart
```

Replace `DP-3` with your gaming monitor's output name (`kscreen-doctor -o` on KDE). Omit `--monitor` to let the compositor choose. On multiple monitors, an explicit output avoids displaying on the wrong screen. Omit `--autostart` if you prefer manual launch. `--combined --autostart` backs up and disables earlier user Discord/overlay autostart entries to prevent duplicate launches. Omit `--combined` to run only the overlay, or `--move-hotkey` to leave shortcut settings unchanged. The combined launcher finds the native `discord` executable on PATH or the per-user official installation at `~/.local/share/discord-native/discord`. KDE shortcut registration is handled by `kbuildsycoca6`; an existing shortcut conflict may need resolving in System Settings.

Quit an existing Discover Overlay instance, then open **Discord + Activity Overlay** from your application menu (or **Discord Activity Overlay** without `--combined`). Join a voice channel and authorize Discover if asked. The installer backs up existing configuration, keeps the authorization cache local, and merges only appearance/behavior settings.

If your own speaking ring stays dark inside Discord too, select your physical microphone explicitly under Discord's Voice & Video settings. Check any virtual audio processing route.

## Local preview

With the custom overlay running and Discord connected to a voice channel:

```sh
printf '%s\n' --activity-test-40 > "$HOME/.var/app/io.github.trigg.discover_overlay/config/discover_overlay/discover_overlay.rpc"
```

Fake participants join, random groups speak, the display goes quiet, and they leave. The demo cleans itself up after 35 seconds. No messages are sent and no real voice connections are changed. Stay in the same channel during the preview.

## Settings

Local settings live at:

```text
~/.var/app/io.github.trigg.discover_overlay/config/discover_overlay/config.ini
```

Discover reloads appearance settings automatically. Do not publish this file: it can contain an authorization token in its cache section. `theme.ini` in this repository contains only appearance and behavior defaults.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests simulate events without contacting Discord. Startup and the 40-person preview were exercised locally; actual connection loss has not been forced during testing.

## Disable

Quit Discord to stop the combined launcher and overlay. For standalone use, quit Discord Activity Overlay. Remove its entries from your desktop's Autostart and Shortcuts settings if enabled. Launch the regular Discover Overlay to use it without this extension. To restore earlier appearance settings, use the installer's local `config.ini.backup`; it can contain credentials, so keep it private.

## Credits

Discover Overlay provides rendering and Discord integration and is licensed GPL-3.0-or-later. This repository contains the extension and setup files, not a copy of Discover or Discord. Not affiliated with Discord or Discover's maintainers.
