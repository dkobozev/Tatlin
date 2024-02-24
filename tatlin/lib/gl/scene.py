# -*- coding: utf-8 -*-
# Copyright (C) 2011 Denis Kobozev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


import math
from typing import Any

from OpenGL.GL import *  # type:ignore
from OpenGL.GLU import *  # type:ignore
from OpenGL.GLUT import *  # type:ignore

from tatlin.lib.ui.basescene import BaseScene

from .model import Model
from .views import View2D, View3D
from .util import html_color


class Scene(BaseScene):
    """
    A scene is responsible for displaying a model and accompanying objects (actors).

    In addition to calling display functions on its actors, the scene is also
    responsible for viewing transformations such as zooming, panning and
    rotation, as well as being the interface for the actors.
    """

    PAN_SPEED = 25
    ROTATE_SPEED = 25

    def __init__(self, parent):
        super(Scene, self).__init__(parent)

        self.model: Any = None
        self.actors = []
        self.cursor_x = 0
        self.cursor_y = 0

        self.view_ortho = View2D()
        self.view_perspective = View3D()
        self.current_view = self.view_perspective

    def add_model(self, model):
        self.model = model
        self.actors.append(self.model)

    def export_to_file(self, model_file):
        """
        Write model to file.
        """
        model_file.write_stl(self.model)
        self.model.modified = False

    def add_supporting_actor(self, actor):
        self.actors.append(actor)

    def clear(self):
        self.actors = []

    # ------------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------------

    def init(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)  # set clear color to black
        glClearDepth(1.0)  # set depth value to 1
        glDepthFunc(GL_LEQUAL)

        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        # simulate translucency by blending colors
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.init_actors()

        self.initialized = True

    def init_actors(self):
        for actor in self.actors:
            if not actor.initialized:
                actor.init()

    def display(self, w, h):
        # clear the color and depth buffers from any leftover junk
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # type:ignore

        # discard back-facing polygons
        glCullFace(GL_BACK)

        # fix normals after scaling to prevent problems with lighting
        # see: http://www.opengl.org/resources/faq/technical/lights.htm#ligh0090
        glEnable(GL_RESCALE_NORMAL)

        glutInit()

        self.view_ortho.begin(w, h)
        self.draw_axes()
        self.view_ortho.end()

        self.current_view.begin(w, h)
        self.current_view.display_transform()

        if self.mode_ortho:
            for actor in self.actors:
                actor.display(
                    elevation=-self.current_view.elevation,
                    mode_ortho=self.mode_ortho,
                    mode_2d=self.mode_2d,
                )
        else:
            # actors may use eye height to perform rendering optimizations; in
            # the simplest terms, in the most convenient definitions, eye
            # height in the perspective projection divides the screen into two
            # horizontal halves - one seen from above, the other from below
            y = self.current_view.y / self.current_view.zoom_factor
            z = self.current_view.z
            angle = -math.degrees(math.atan2(z, y)) - self.current_view.elevation
            eye_height = math.sqrt(y**2 + z**2) * math.sin(math.radians(angle))

            # draw line of sight plane
            """
            #plane_size = 200
            #glBegin(GL_LINES)
            #glColor(1.0, 0.0, 0.0)
            #glVertex(-plane_size/2, plane_size/2, eye_height)
            #glVertex(plane_size/2, plane_size/2, eye_height)

            #glVertex(plane_size/2, plane_size/2, eye_height)
            #glVertex(plane_size/2, -plane_size/2, eye_height)

            #glVertex(plane_size/2, -plane_size/2, eye_height)
            #glVertex(-plane_size/2, -plane_size/2, eye_height)

            #glVertex(-plane_size/2, -plane_size/2, eye_height)
            #glVertex(-plane_size/2, plane_size/2, eye_height)
            #glEnd()
            """

            for actor in self.actors:
                actor.display(
                    eye_height=eye_height,
                    mode_ortho=self.mode_ortho,
                    mode_2d=self.mode_2d,
                )

        self.current_view.end()

    def reshape(self, w, h):
        glViewport(0, 0, w, h)

    def draw_axes(self, length=50.0):
        glPushMatrix()
        self.current_view.ui_transform(length)

        axes = [
            (-length, 0.0, 0.0),
            (0.0, -length, 0.0),
            (0.0, 0.0, length),
        ]
        colors = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), html_color("008aff")]
        labels = ["x", "y", "z"]

        glBegin(GL_LINES)

        for axis, color in zip(axes, colors):
            glColor(*color)
            glVertex(0.0, 0.0, 0.0)
            glVertex(*axis)

        glEnd()

        # draw axis labels
        for label, axis, color in zip(labels, axes, colors):
            glColor(*color)
            # add padding to labels
            glRasterPos(axis[0] + 2, axis[1] + 2, axis[2] + 2)
            glutBitmapCharacter(GLUT_BITMAP_8_BY_13, ord(label))  # type:ignore

        glPopMatrix()

    # ------------------------------------------------------------------------
    # VIEWING MANIPULATIONS
    # ------------------------------------------------------------------------

    def button_press(self, x, y):
        self.cursor_x = x
        self.cursor_y = y

    def button_motion(self, x, y, left, middle, right):
        delta_x = x - self.cursor_x
        delta_y = y - self.cursor_y

        if left:
            self.current_view.rotate(
                delta_x * self.ROTATE_SPEED / 100, delta_y * self.ROTATE_SPEED / 100
            )
        elif middle:
            if hasattr(self.current_view, "offset"):
                self.current_view.offset(  # type:ignore
                    delta_x * self.PAN_SPEED / 100, delta_y * self.PAN_SPEED / 100
                )
        elif right:
            self.current_view.pan(
                delta_x * self.PAN_SPEED / 100, delta_y * self.PAN_SPEED / 100
            )

        self.cursor_x = x
        self.cursor_y = y

        self.invalidate()

    def wheel_scroll(self, direction):
        delta_y = 30.0
        if direction < 0:
            direction = -1
        else:
            direction = 1
        delta_y = direction * delta_y

        self.current_view.zoom(0, delta_y)
        self.invalidate()

    def reset_view(self, both=False):
        if both:
            self.view_ortho.reset_state()
            self.view_perspective.reset_state()
        else:
            self.current_view.reset_state()

    @property
    def mode_2d(self):
        return isinstance(self.current_view, View2D)

    @mode_2d.setter
    def mode_2d(self, value):
        self.current_view = self.view_ortho if value else self.view_perspective

    @property
    def mode_ortho(self):
        return (
            self.current_view.supports_ortho and self.current_view.ortho  # type:ignore
        )

    @mode_ortho.setter
    def mode_ortho(self, value):
        if self.current_view.supports_ortho:
            self.current_view.ortho = value  # type:ignore

    def rotate_view(self, azimuth, elevation):
        if not self.mode_2d:
            self.current_view.azimuth = azimuth
            self.current_view.elevation = elevation
            self.invalidate()

    def view_model_center(self):
        """
        Display the model in the center of the scene without modifying the vertices.
        """
        bounding_box = self.model.bounding_box
        lower_corner = bounding_box.lower_corner
        upper_corner = bounding_box.upper_corner
        self.model.offset_x = -(upper_corner[0] + lower_corner[0]) / 2
        self.model.offset_y = -(upper_corner[1] + lower_corner[1]) / 2
        self.model.offset_z = -lower_corner[2]

    # ------------------------------------------------------------------------
    # MODEL MANIPULATION
    # ------------------------------------------------------------------------

    def change_num_layers(self, number):
        """
        Change number of visible layers for Gcode model.
        """
        self.model.num_layers_to_draw = number

    def scale_model(self, factor):
        print("--- scaling model by factor of:", factor)
        self.model.scale(factor)
        self.model.init()

    def center_model(self):
        """
        Center the model on platform and raise its lowest point to z=0.
        """
        bounding_box = self.model.bounding_box
        lower_corner = bounding_box.lower_corner
        upper_corner = bounding_box.upper_corner
        offset_x = -(upper_corner[0] + lower_corner[0]) / 2
        offset_y = -(upper_corner[1] + lower_corner[1]) / 2
        offset_z = -lower_corner[2]
        self.model.translate(offset_x, offset_y, offset_z)
        self.model.init()

    def change_model_dimension(self, dimension, value):
        current_value = getattr(self.model, dimension)
        # since our scaling is absolute, we have to take current scaling factor
        # into account
        factor = (value / current_value) * self.model.scaling_factor
        self.scale_model(factor)

    def rotate_model(self, angle, axis_name):
        axis = Model.letter_axis_map[axis_name]
        self.model.rotate_abs(angle, axis)
        self.model.init()

    def show_arrows(self, show):
        self.model.arrows_enabled = show
        self.model.init()

    @property
    def model_modified(self):
        """
        Return true when an important model property has been modified.

        Important properties exclude viewing transformations and can be
        something like size, shape or color.
        """
        return self.model and self.model.modified
