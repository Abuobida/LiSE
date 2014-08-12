# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
from kivy.properties import (
    DictProperty,
    ObjectProperty,
    NumericProperty,
    ListProperty,
    AliasProperty
)
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from .spot import Spot
from .arrow import Arrow
from .pawn import Pawn


class BoardLayout(FloatLayout):
    def on_touch_down(self, touch):
        for child in self.children:
            if child.on_touch_down(touch):
                return child

    def on_touch_move(self, touch):
        for child in self.children:
            child.on_touch_move(touch)

    def on_touch_up(self, touch):
        for child in self.children:
            if child.on_touch_up(touch):
                return child


class Board(RelativeLayout):
    """A graphical view onto a facade, resembling a game board."""
    layout = ObjectProperty()
    character = ObjectProperty()
    spot = DictProperty({})
    pawn = DictProperty({})
    arrow = DictProperty({})
    arrow_bg = ListProperty()
    arrow_fg = ListProperty()
    arrow_width = NumericProperty()
    arrowhead_size = NumericProperty()
    spotlayout = AliasProperty(
        lambda self: self.layout.ids.spotlayout,
        lambda self, v: None
    )
    pawnlayout = AliasProperty(
        lambda self: self.layout.ids.pawnlayout,
        lambda self, v: None
    )
    arrowlayout = AliasProperty(
        lambda self: self.layout.ids.arrowlayout,
        lambda self, v: None
    )
    app = AliasProperty(
        lambda self: self.layout.app,
        lambda self, v: None
    )
    engine = AliasProperty(
        lambda self: self.layout.app.engine,
        lambda self, v: None
    )

    def __init__(self, **kwargs):
        self._trigger_redata = Clock.create_trigger(self._redata)
        super().__init__(**kwargs)
        self._trigger_redata()

    def _make_pawn(self, thing):
        if thing["location"] not in self.spot:
            raise ValueError("Pawns should only be made after the Spot their Thing is on")
        if thing["name"] in self.pawn:
            raise KeyError("Already have a Pawn for this Thing")
        r = Pawn(
            board=self,
            thing=thing,
            where_upon=self.spot[thing["location"]]
        )
        self.spot[thing["location"]].pawns_here.append(r)
        self.pawn[thing["name"]] = r
        return r

    def _make_spot(self, place):
        if place["name"] in self.spot:
            raise KeyError("Already have a Spot for this Place")
        r = Spot(
            board=self,
            place=place
        )
        self.spot[place["name"]] = r
        return r

    def _make_arrow(self, portal):
        if (
                portal["origin"] not in self.spot or
                portal["destination"] not in self.spot
        ):
            raise ValueError("Arrows should only be made after the Spots they connect")
        if (
                portal["origin"] in self.arrow and
                portal["destination"] in self.arrow
        ):
            raise KeyError("Already have an Arrow for this Portal")
        r = Arrow(
            board=self,
            engine=self.engine,
            portal=portal
        )
        if portal["origin"] not in self.arrow:
            self.arrow[portal["origin"]] = {}
        self.arrow[portal["origin"]][portal["destination"]] = r
        return r

    def on_character(self, *args):
        def ontime():
            self._trigger_redata()

        def updscrollx(*args):
            self.character.stat['_scroll_x'] = self.parent.scroll_x
        trigger_updscrollx = Clock.create_trigger(updscrollx)

        def updscrolly(*args):
            self.character.stat['_scroll_y'] = self.parent.scroll_y
        trigger_updscrolly = Clock.create_trigger(updscrolly)

        for prop in '_scroll_x', '_scroll_y':
            if prop not in self.character.stat:
                self.character.stat[prop] = 0.0

        self.parent.scroll_x = self.character.stat['_scroll_x']
        self.parent.scroll_y = self.character.stat['_scroll_y']
        self.parent.bind(scroll_x=trigger_updscrollx)
        self.parent.bind(scroll_y=trigger_updscrolly)
        self.engine.on_time(ontime, name=self.character.name + "_trigger_redata")
        self._trigger_redata()

    def _rmpawn(self, name):
        if name not in self.pawn:
            raise KeyError("No Pawn")
        self.pawnlayout.remove_widget(self.pawn[name])
        del self.pawn[name]

    def _rmspot(self, name):
        if name not in self.spot:
            raise KeyError("No Spot")
        self.spotlayout.remove_widget(self.pawn[name])
        del self.spot[name]

    def _rmarrow(self, orig, dest):
        if (
                orig not in self.arrow or
                dest not in self.arrow[orig]
        ):
            raise KeyError("No Arrow")
        self.spotlayout.remove_widget(self.arrow[orig][dest])
        del self.arrow[orig][dest]

    def _redata(self, *args):
        # remove widgets that don't represent anything anymore
        for pawn_name in self.pawn:
            if pawn_name not in self.character.thing:
                self._rmpawn(pawn_name)
        for spot_name in self.spot:
            if spot_name not in self.character.place:
                self._rmspot(spot_name)
        for arrow_origin in self.arrow:
            for arrow_destination in self.arrow[arrow_origin]:
                if (
                        arrow_origin not in self.character.portal or
                        arrow_destination not in self.character.portal[arrow_origin]
                ):
                    self._rmarrow(arrow_origin, arrow_destination)
        # add widgets to represent new stuff
        for place_name in self.character.place:
            if place_name not in self.spot:
                self.spotlayout.add_widget(self._make_spot(self.character.place[place_name]))
        for arrow_orig in self.character.portal:
            for arrow_dest in self.character.portal[arrow_orig]:
                if (
                        arrow_orig not in self.arrow or
                        arrow_dest not in self.arrow[arrow_orig]
                ):
                    self.arrowlayout.add_widget(self._make_arrow(self.character.portal[arrow_orig][arrow_dest]))
        for thing_name in self.character.thing:
            if thing_name not in self.pawn:
                self.pawnlayout.add_widget(self._make_pawn(self.character.thing[thing_name]))

    def __repr__(self):
        return "Board({})".format(repr(self.character))

    def on_touch_down(self, touch):
        touch.push()
        touch.apply_transform_2d(self.parent.to_local)
        r = self.pawnlayout.on_touch_down(touch)
        if r:
            touch.pop()
            self.layout.grabbed = r
            return r
        r = self.spotlayout.on_touch_down(touch)
        if r:
            touch.pop()
            self.layout.grabbed = r
            return r
        r = self.arrowlayout.on_touch_down(touch)
        if r:
            touch.pop()
            return r
        touch.pop()
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        touch.push()
        touch.apply_transform_2d(self.parent.to_local)
        self.pawnlayout.on_touch_move(touch)
        self.spotlayout.on_touch_move(touch)
        self.arrowlayout.on_touch_move(touch)
        touch.pop()
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        touch.push()
        touch.apply_transform_2d(self.parent.to_local)
        self.layout.grabbed = None
        r = self.pawnlayout.on_touch_up(touch)
        if r:
            touch.pop()
            return r
        r = self.spotlayout.on_touch_up(touch)
        if r:
            touch.pop()
            return r
        r = self.arrowlayout.on_touch_up(touch)
        if r:
            touch.pop()
            return r
        touch.pop()
        return super().on_touch_up(touch)
