# coding=utf8
# BézierBuilder
#
# Copyright (c) 2013, Juan Luis Cano Rodríguez <juanlu001@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER
# OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""BézierBuilder, an interactive Bézier curve explorer.

Just run it with

$ python bezier_builder.py

"""

import threading

import numpy as np
from scipy.special import binom

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .minimvc import Trigger

class BezierModel(object):
    def __init__(self, xp, yp):
        self.lock = threading.RLock()
        self._xp = list(xp)
        self._yp = list(yp)

        self.trigger = Trigger()

    def get_control_points(self):
        with self.lock:
            return list(self._xp), list(self._yp)

    def get_bezier_points(self, num=200):
        with self.lock:
            x, y = Bezier(list(zip(self._xp, self._yp))).T
            return x, y

    def add_point(self, i, new_x, new_y):
        with self.lock:
            self._xp.insert(i, new_x)
            self._yp.insert(i, new_y)
        self.trigger.fire()

    def remove_point(self, i):
        with self.lock:
            del self._xp[i]
            del self._yp[i]
        self.trigger.fire()

    def move_point(self, i, new_x, new_y):
        with self.lock:
            self._xp[i] = new_x
            self._yp[i] = new_y
        self.trigger.fire()

class BezierBuilder(object):
    """Bézier curve interactive builder.

    """
    def __init__(self, ax, bezier_model):
        self.ax = ax
        self.bezier_model = bezier_model

        self.canvas = self.ax.figure.canvas
        xp, yp = self.bezier_model.get_control_points()
        self.control_polygon = Line2D(xp, yp,
                                      ls="--", c="#666666", marker="x",
                                      mew=2, mec="#204a87")
        self.ax.add_line(self.control_polygon)
        x, y = self.bezier_model.get_bezier_points()
        self.bezier_curve = Line2D(x, y)
        self.ax.add_line(self.bezier_curve)

        # Event handler for mouse clicking
        self.canvas.mpl_connect('button_press_event', self.on_button_press)
        self.canvas.mpl_connect('button_release_event', self.on_button_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion_notify)

        self._index = None  # Active vertex

        self.bezier_model.trigger.add_callback(self._refresh)
        self._refresh()

    def __del__(self):
        self.bezier_model.remove_callback(self._refresh)

    def on_button_press(self, event):
        # Ignore clicks outside axes
        if event.inaxes != self.ax: return
        res, ind = self.control_polygon.contains(event)
        if res and event.key is None:
            # Grabbing a point to drag
            self._index = ind["ind"][0]
        if res and event.key == "control":
            # Control-click deletes
            self.bezier_model.remove_point(ind["ind"][0])
        if event.key == "shift":
            # Adding a new point. Find the two closest points and insert it in
            # between them.
            total_squared_dists = []
            xp, yp = self.bezier_model.get_control_points()
            for i in range(len(xp) - 1):
                dist = (event.xdata - xp[i]) ** 2
                dist += (event.ydata - yp[i]) ** 2
                dist += (event.xdata - xp[i + 1]) ** 2
                dist += (event.ydata - yp[i + 1]) ** 2
                total_squared_dists.append(dist)
            best = np.argmin(total_squared_dists)

            self.bezier_model.add_point(best + 1, event.xdata, event.ydata)

    def on_button_release(self, event):
        if event.button != 1: return
        self._index = None

    def on_motion_notify(self, event):
        if event.inaxes != self.ax: return
        if self._index is None: return
        x, y = event.xdata, event.ydata

        self.bezier_model.move_point(self._index, x, y)

    def _refresh(self):
        with self.bezier_model.lock:
            xp, yp = self.bezier_model.get_control_points()
            self.control_polygon.set_data(xp, yp)
            x, y = self.bezier_model.get_bezier_points()
            self.bezier_curve.set_data(x, y)
            self.canvas.draw()

def Bernstein(n, k):
    """Bernstein polynomial.

    """
    coeff = binom(n, k)

    def _bpoly(x):
        return coeff * x ** k * (1 - x) ** (n - k)

    return _bpoly


def Bezier(points, num=200):
    """Build Bézier curve from points.

    """
    N = len(points)
    t = np.linspace(0, 1, num=num)
    curve = np.zeros((num, 2))
    for ii in range(N):
        curve += np.outer(Bernstein(N - 1, ii)(t), points[ii])
    return curve
