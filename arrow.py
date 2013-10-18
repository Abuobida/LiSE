# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
from __future__ import print_function
from math import cos, sin
from util import (
    wedge_offsets_rise_run,
    truncated_line,
    fortyfive)
from kivy.graphics import Line, Color
from kivy.uix.widget import Widget
from kivy.properties import AliasProperty, DictProperty, ObjectProperty


class Arrow(Widget):
    margin = 20
    w = 1
    board = ObjectProperty()
    portal = ObjectProperty()
    rowdict = DictProperty()

    def __init__(self, **kwargs):
        Widget.__init__(self, **kwargs)
        self.upd_rowdict()
        dimn = unicode(self.board.dimension)
        orign = unicode(self.portal.origin)
        destn = unicode(self.portal.destination)
        self.board.spotdict[orign].bind(transform=self.realign)
        self.board.spotdict[destn].bind(transform=self.realign)
        self.board.closet.skeleton["portal"][dimn][orign][destn].bind(
            touches=self.upd_rowdict)
        self.bg_color = Color(0.25, 0.25, 0.25)
        self.fg_color = Color(1.0, 1.0, 1.0)
        self.bg_line = Line(points=self.get_points(), width=self.w * 1.4)
        self.fg_line = Line(points=self.get_points(), width=self.w)
        self.canvas.add(self.bg_color)
        self.canvas.add(self.bg_line)
        self.canvas.add(self.fg_color)
        self.canvas.add(self.fg_line)

    @property
    def reciprocal(self):
        # Return the edge of the portal that connects the same two
        # places in the opposite direction, supposing it exists
        try:
            return self.portal.reciprocal.arrow
        except KeyError:
            return None

    @property
    def selected(self):
        return self in self.board.selected

    @property
    def orig(self):
        return self.board.spotdict[unicode(self.portal.origin)]

    @property
    def dest(self):
        return self.board.spotdict[unicode(self.portal.destination)]

    def upd_rowdict(self, *args):
        self.rowdict = self.board.closet.skeleton["portal"][
            unicode(self.board.dimension)][unicode(self.portal.origin)][
            unicode(self.portal.destination)]

    def get_points(self):
        (ox, oy) = self.orig.to_parent(*self.orig.get_coords(), relative=True)
        (dx, dy) = self.dest.to_parent(*self.dest.get_coords(), relative=True)
        (dw, dh) = self.dest.get_size()
        drx = dw / 2
        dry = dh / 2
        if drx > dry:
            dr = drx
        else:
            dr = dry
        if dy < oy:
            yco = -1
        else:
            yco = 1
        if dx < ox:
            xco = -1
        else:
            xco = 1
        (leftx, boty, rightx, topy) = truncated_line(
            float(ox * xco), float(oy * yco),
            float(dx * xco), float(dy * yco),
            dr + 1)
        taillen = float(self.board.arrowhead_size)
        rise = topy - boty
        run = rightx - leftx
        if rise == 0:
            xoff1 = cos(fortyfive) * taillen
            yoff1 = xoff1
            xoff2 = xoff1
            yoff2 = -1 * yoff1
        elif run == 0:
            xoff1 = sin(fortyfive) * taillen
            yoff1 = xoff1
            xoff2 = -1 * xoff1
            yoff2 = yoff1
        else:
            (xoff1, yoff1, xoff2, yoff2) = wedge_offsets_rise_run(
                rise, run, taillen)
        x1 = (rightx - xoff1) * xco
        x2 = (rightx - xoff2) * xco
        y1 = (topy - yoff1) * yco
        y2 = (topy - yoff2) * yco
        endx = rightx * xco
        endy = topy * yco
        return [ox, oy,
                endx, endy, x1, y1,
                endx, endy, x2, y2,
                endx, endy]

    def get_slope(self):
        ox = self.orig.x
        oy = self.orig.y
        dx = self.dest.x
        dy = self.dest.y
        if oy == dy:
            return 0
        elif ox == dx:
            return None
        else:
            return self.rise / self.run

    def get_left(self):
        if self.orig.x < self.dest.x:
            return self.orig.x - self.margin
        else:
            return self.dest.x - self.margin

    def get_right(self):
        if self.orig.x < self.dest.x:
            return self.dest.x + self.margin
        else:
            return self.orig.x + self.margin

    def get_bot(self):
        if self.orig.y < self.dest.y:
            return self.orig.y - self.margin
        else:
            return self.dest.y - self.margin

    def get_top(self):
        if self.orig.y < self.dest.y:
            return self.dest.y + self.margin
        else:
            return self.orig.y + self.margin

    def get_b(self):
        if self.m is None:
            return None
        denominator = self.run
        x_numerator = self.rise * self.ox
        y_numerator = denominator * self.oy
        return ((y_numerator - x_numerator), denominator)

    def realign(self, *args):
        points = self.get_points()
        self.bg_line.points = points
        self.fg_line.points = points
