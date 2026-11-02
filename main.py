

#!/usr/bin/env python3

import gi
import sys
import threading
import cairo

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")

from gi.repository import Gtk, GtkLayerShell, GLib
from OpenGL import GL
from pathlib import Path


ROOT = Path(__file__).parent
SHADERS = ROOT / "shaders"

WIDTH = 1920
HEIGHT = 1080
CHANNELS = 3

FRAME_SIZE = WIDTH * HEIGHT * CHANNELS


class LiveWallpaper:

    def __init__(self):

        self.frame = None
        self.frame_lock = threading.Lock()
        self.running = True

        self.program = None
        self.vao = None
        self.texture = None

        self.window = Gtk.Window()
        self.window.set_decorated(False)

        GtkLayerShell.init_for_window(self.window)

        GtkLayerShell.set_namespace(
            self.window, "my-wallpaper"
        )

        GtkLayerShell.set_layer(
            self.window,
            GtkLayerShell.Layer.BACKGROUND
        )

        for edge in (
            GtkLayerShell.Edge.TOP,
            GtkLayerShell.Edge.BOTTOM,
            GtkLayerShell.Edge.LEFT,
            GtkLayerShell.Edge.RIGHT
        ):
            GtkLayerShell.set_anchor(
                self.window, edge, True
            )

        GtkLayerShell.set_exclusive_zone(
            self.window, 0
        )

        GtkLayerShell.set_keyboard_interactivity(
            self.window, False
        )

        self.area = Gtk.GLArea()
        self.area.set_required_version(3, 3)
        self.area.set_use_es(False)
        self.area.set_has_depth_buffer(False)
        self.area.set_auto_render(False)

        self.area.connect("realize", self.on_gl_realize)
        self.area.connect("render", self.on_render)

        self.window.add(self.area)
        self.window.connect("realize", self.on_window_realize)

        self.window.show_all()

        # Read video from stdin in a background thread
        self.reader = threading.Thread(
            target=self.read_frames,
            daemon=True
        )
        self.reader.start()

        GLib.timeout_add(16, self.update)

    def on_window_realize(self, window):

        gdk_window = window.get_window()

        gdk_window.input_shape_combine_region(
            cairo.Region(), 0, 0
        )

    def read_frames(self):

        while self.running:

            data = sys.stdin.buffer.read(FRAME_SIZE)

            if len(data) != FRAME_SIZE:
                break

            with self.frame_lock:
                self.frame = data

    def compile_shader(self, filename, shader_type):

        source = (SHADERS / filename).read_text()

        shader = GL.glCreateShader(shader_type)

        GL.glShaderSource(shader, source)
        GL.glCompileShader(shader)

        if not GL.glGetShaderiv(
            shader, GL.GL_COMPILE_STATUS
        ):
            raise RuntimeError(
                GL.glGetShaderInfoLog(shader)
            )

        return shader

    def on_gl_realize(self, area):

        area.make_current()

        error = area.get_error()

        if error:
            print("OpenGL error:", error)
            return

        vertex = self.compile_shader(
            "vertex.glsl", GL.GL_VERTEX_SHADER
        )

        fragment = self.compile_shader(
            "fragment.glsl", GL.GL_FRAGMENT_SHADER
        )

        self.program = GL.glCreateProgram()

        GL.glAttachShader(self.program, vertex)
        GL.glAttachShader(self.program, fragment)

        GL.glLinkProgram(self.program)

        if not GL.glGetProgramiv(
            self.program, GL.GL_LINK_STATUS
        ):
            raise RuntimeError(
                GL.glGetProgramInfoLog(self.program)
            )

        GL.glDeleteShader(vertex)
        GL.glDeleteShader(fragment)

        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        # Create video texture
        self.texture = GL.glGenTextures(1)

        GL.glBindTexture(
            GL.GL_TEXTURE_2D, self.texture
        )

        GL.glTexParameteri(
            GL.GL_TEXTURE_2D,
            GL.GL_TEXTURE_MIN_FILTER,
            GL.GL_LINEAR
        )

        GL.glTexParameteri(
            GL.GL_TEXTURE_2D,
            GL.GL_TEXTURE_MAG_FILTER,
            GL.GL_LINEAR
        )

        GL.glTexParameteri(
            GL.GL_TEXTURE_2D,
            GL.GL_TEXTURE_WRAP_S,
            GL.GL_CLAMP_TO_EDGE
        )

        GL.glTexParameteri(
            GL.GL_TEXTURE_2D,
            GL.GL_TEXTURE_WRAP_T,
            GL.GL_CLAMP_TO_EDGE
        )

        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)

        # Allocate texture storage
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,
            GL.GL_RGB8,
            WIDTH,
            HEIGHT,
            0,
            GL.GL_RGB,
            GL.GL_UNSIGNED_BYTE,
            None
        )

        GL.glUseProgram(self.program)

        location = GL.glGetUniformLocation(
            self.program, "u_video"
        )

        GL.glUniform1i(location, 0)

        print("OpenGL video renderer initialized")

    def on_render(self, area, context):

        if self.program is None:
            return True

        with self.frame_lock:
            frame = self.frame
            self.frame = None

        if frame is not None:

            GL.glBindTexture(
                GL.GL_TEXTURE_2D, self.texture
            )

            GL.glTexSubImage2D(
                GL.GL_TEXTURE_2D,
                0,
                0, 0,
                WIDTH, HEIGHT,
                GL.GL_RGB,
                GL.GL_UNSIGNED_BYTE,
                frame
            )

        GL.glViewport(
            0, 0,
            *GL.glGetIntegerv(GL.GL_VIEWPORT)[2:]
        )

        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        GL.glUseProgram(self.program)

        GL.glActiveTexture(GL.GL_TEXTURE0)

        GL.glBindTexture(
            GL.GL_TEXTURE_2D, self.texture
        )

        GL.glBindVertexArray(self.vao)

        GL.glDrawArrays(
            GL.GL_TRIANGLES, 0, 3
        )

        return True

    def update(self):

        self.area.queue_render()
        return True


if __name__ == "__main__":

    if not GtkLayerShell.is_supported():
        raise RuntimeError("Layer shell unsupported")

    wallpaper = LiveWallpaper()
    Gtk.main()
