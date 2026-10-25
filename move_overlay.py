#!/usr/bin/env python3
"""Toggle overlay placement; run inside Discover's Flatpak runtime."""
import configparser
import fcntl
import os
from pathlib import Path
import socket
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell
from discover_overlay.draggable_window_wayland import DraggableWindowWayland

Gtk.init([])
lock_path = Path(os.environ['XDG_CACHE_HOME']) / 'overlay-move.lock'
lock_path.parent.mkdir(parents=True, exist_ok=True)
lock = lock_path.open('a+')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    client = socket.socket(socket.AF_UNIX)
    client.connect(str(lock_path.with_suffix('.sock')))
    client.sendall(b'save')
    client.close()
    raise SystemExit
lock.seek(0)
lock.truncate()
lock.write(str(os.getpid()))
lock.flush()
config_path = Path(os.environ['XDG_CONFIG_HOME']) / 'discover_overlay/config.ini'
c = configparser.ConfigParser(interpolation=None)
c.read(config_path)
display = Gdk.Display.get_default()
screen = Gdk.Screen.get_default()
monitor = 0
for i in range(display.get_n_monitors()):
    if screen.get_monitor_plug_name(i) == c.get('main', 'monitor', fallback='Any'):
        monitor = i

class Placement:
    def change_placement(self, window):
        # Re-read to preserve settings or authorization changed while moving.
        current = configparser.ConfigParser(interpolation=None)
        current.read(config_path)
        for key, value in zip(('floating_x', 'floating_y', 'floating_w', 'floating_h'), window.get_coords()):
            current.set('main', key, str(value))
        current.set('main', 'floating', 'True')
        current.set('main', 'topalign', '0')
        with config_path.open('w') as handle:
            current.write(handle)
        window.destroy()
        Gtk.main_quit()

placement = Placement()
window = DraggableWindowWayland(
    pos_x=c.getfloat('main', 'floating_x', fallback=.015),
    pos_y=c.getfloat('main', 'floating_y', fallback=.04),
    width=c.getfloat('main', 'floating_w', fallback=.28),
    height=c.getfloat('main', 'floating_h', fallback=.7),
    message='Drag to move; resize edges. Click green or press Shift+~ again to save.',
    settings=placement, monitor=monitor)
GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
def save():
    placement.change_placement(window)
    return False
socket_path = lock_path.with_suffix('.sock')
socket_path.unlink(missing_ok=True)
server = socket.socket(socket.AF_UNIX)
server.bind(str(socket_path))
server.listen(1)
def receive_save(_source, _condition):
    client, _ = server.accept()
    client.recv(16)
    client.close()
    save()
    return False
GLib.io_add_watch(server, GLib.IO_IN, receive_save)
Gtk.main()
