# This file is part of LiSE, a framework for life simulation games.
# Copyright (C) 2013-2014 Zachary Spector, ZacharySpector@gmail.com
"""Classes to listen to changes in the simulation from elsewhere, such
as in the user interface.

"""
from functools import partial
from kivy.event import EventDispatcher
from kivy.properties import (
    DictProperty,
    ObjectProperty,
    NumericProperty,
    StringProperty,
    ReferenceListProperty
)
from kivy.clock import Clock
from kivy.logger import Logger
from .util import trigger


class MirrorMapping(EventDispatcher):
    """Holds a :class:`DictProperty`, ``mirror``, which always has the
    value of the LiSE entity, ``remote``, that the user should see at
    the moment.

    """
    branch = StringProperty('master')
    tick = NumericProperty(0)
    time = ReferenceListProperty(branch, tick)
    remote = ObjectProperty()
    mirror = DictProperty({})

    def on_time(self, *args):
        """Update the mirror whenever the time changes."""
        if not self.remote:
            Clock.schedule_once(self.on_time, 0)
            return
        self.mirror = dict(self.remote)

    def sync(self, *args):
        """Copy remote's data to the mirror."""
        data = {}
        for (k, v) in self.remote.items():
            if v is not None:
                assert(len(k) > 0)
                data[k] = v

        self.mirror = data
    _trigger_sync = trigger(sync)

    def listen(self, *args, **kwargs):
        """Make sure to stay in sync with all changes to remote.

        With keyword argument ``stat``, sync with only that stat.

        """
        remote = kwargs.get('remote', None) or self.remote
        remote.listener(
            fun=self._listen_func,
            stat=kwargs.get('stat', None)
        )

    def unlisten(self, *args, **kwargs):
        """Stop listening to remote.

        With keyword argument ``stat``, stop listening to that stat,
        but keep listening to the others.

        """
        remote = kwargs.get('remote', None) or self.remote
        remote.unlisten(
            fun=self._listen_func,
            stat=kwargs.get('stat', None)
        )

    def _listen_func(self, branch, tick, what, k, v):
        if k in self.mirror and self.mirror[k] == v:
            return
        elif v is None and k in self.mirror:
            if k in ('next_location', 'next_arrival_time'):
                self.mirror[k] = None
                return
            del self.mirror[k]
        elif v is not None:
            self.mirror[k] = v