#!/usr/bin/env python3

import gi
import math
import time
import cairo

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")

from gi.repository import Gtk, GtkLayerShell, GLib, Gdk


class LiveWallpaper:

    def __init__(self):
        self.start_time = time.monotonic()

        self.window = Gtk.Window()

        # Initialize Wayland layer shell
        GtkLayerShell.init_for_window(self.window)

        GtkLayerShell.set_namespace(
            self.window, "my-wallpaper"
        )

        GtkLayerShell.set_layer(
            self.window,
            GtkLayerShell.Layer.BACKGROUND
        )

        # Cover the entire output
        for edge in (
            GtkLayerShell.Edge.TOP,
            GtkLayerShell.Edge.BOTTOM,
            GtkLayerShell.Edge.LEFT,
            GtkLayerShell.Edge.RIGHT
        ):
            GtkLayerShell.set_anchor(
                self.window, edge, True
            )

        # Don't reserve desktop space
        GtkLayerShell.set_exclusive_zone(self.window, 0)

        # Drawing area
        self.area = Gtk.DrawingArea()
        self.area.connect("draw", self.draw)

        self.window.add(self.area)

        # Make the wallpaper transparent to mouse input
        self.window.connect("realize", self.on_realize)

        self.window.show_all()

        # Update at approximately 60 FPS
        GLib.timeout_add(16, self.update)

    def on_realize(self, window):
        gdk_window = window.get_window()
        gdk_window.input_shape_combine_region(
            cairo.Region(), 0, 0
        )

    def update(self):
        self.area.queue_draw()
        return True

    def draw(self, widget, cr):

        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        t = time.monotonic() - self.start_time

        # Background gradient
        gradient = cairo.LinearGradient(
            0, 0, width, height
        )

        gradient.add_color_stop_rgb(
            0, 0.025, 0.015, 0.12
        )

        gradient.add_color_stop_rgb(
            1, 0.12, 0.025, 0.20
        )

        cr.set_source(gradient)
        cr.paint()

        # Animated particles
        for i in range(35):

            x = (
                width * (i % 7) / 7
                + math.sin(t * 0.3 + i) * 100
            )

            y = (
                height * (i // 7) / 5
                + math.cos(t * 0.4 + i) * 100
            )

            radius = 40 + 15 * math.sin(t + i)

            # Soft radial glow
            glow = cairo.RadialGradient(
                x, y, 0,
                x, y, radius
            )

            glow.add_color_stop_rgba(
                0, 0.45, 0.15, 0.85, 0.22
            )

            glow.add_color_stop_rgba(
                1, 0.45, 0.15, 0.85, 0
            )

            cr.set_source(glow)
            cr.arc(x, y, radius, 0, math.pi * 2)
            cr.fill()

        return False


if __name__ == "__main__":

    if not GtkLayerShell.is_supported():
        raise RuntimeError(
            "Wayland layer shell is not supported"
        )

    wallpaper = LiveWallpaper()

    Gtk.main()
