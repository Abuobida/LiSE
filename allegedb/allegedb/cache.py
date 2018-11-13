# This file is part of allegedb, a database abstraction for versioned graphs
# Copyright (c) Zachary Spector. public@zacharyspector.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Classes for in-memory storage and retrieval of historical graph data.
"""
from blinker import Signal
from .window import WindowDict, HistoryError
from collections import OrderedDict, deque


class UnloadedException(KeyError):
    def __init__(self, branch, turn, tick, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        self.turn = turn
        self.tick = tick


class NotCached:
    """Singleton for values that are unknown due to not having been loaded

    Or possibly just not having been cached here yet, though I want to avoid
    that situation.

    """


uncached = NotCached()


class JournalContainer:
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.settings = PickyDefaultDict(SettingsTurnDict)
        self.presettings = PickyDefaultDict(SettingsTurnDict)

    def store(self, *args):
        # overridden in LiSE.cache.InitializedJournalContainer
        entity, key, branch, turn, tick, prev, value = args[-7:]
        parent = args[:-7]
        settings_turns = self.settings[branch]
        presettings_turns = self.presettings[branch]
        if turn in settings_turns or turn in settings_turns.future():
            # These assertions hold for most caches but not for the contents
            # caches, and are therefore commented out.
            # assert turn in presettings_turns or turn in presettings_turns.future()
            setticks = settings_turns[turn]
            # assert tick not in setticks
            presetticks = presettings_turns[turn]
            # assert tick not in presetticks
            presetticks[tick] = parent + (entity, key, prev)
            setticks[tick] = parent + (entity, key, value)
        else:
            presettings_turns[turn] = {tick: parent + (entity, key, prev)}
            settings_turns[turn] = {tick: parent + (entity, key, value)}

    def truncate(self, branch, turn, tick, reverse=False):
        for mapp in (self.settings[branch], self.presettings[branch]):
            if turn in mapp:
                mapp[turn].truncate(tick, reverse=reverse)
            mapp.truncate(turn)


class FuturistWindowDict(WindowDict):
    """A WindowDict that does not let you rewrite the past."""
    __slots__ = ('_future', '_past')

    def __setitem__(self, rev, v):
        if hasattr(v, 'unwrap') and not hasattr(v, 'no_unwrap'):
            v = v.unwrap()
        if self._past is None:
            self._past = []
        if not self._past and not self._future:
            self._past.append((rev, v))
            return
        self.seek(rev)
        if self._future:
            raise HistoryError(
                "Already have some history after {}".format(rev)
            )
        if not self._past or rev > self._past[-1][0]:
            self._past.append((rev, v))
        elif rev == self._past[-1][0]:
            self._past[-1] = (rev, v)
        else:
            raise HistoryError(
                "Already have some history after {} "
                "(and my seek function is broken?)".format(rev)
            )
        if type(self._past) is list and len(self._past) > self.DEQUE_THRESHOLD:
            self._past = deque(self._past)
        if type(self._future) is list and len(self._future) > self.DEQUE_THRESHOLD:
            self._future = deque(self._future)


class TurnDict(FuturistWindowDict):
    __slots__ = ('_future', '_past')
    cls = FuturistWindowDict

    def __getitem__(self, rev):
        try:
            return super().__getitem__(rev)
        except KeyError:
            ret = self[rev] = FuturistWindowDict()
            return ret

    def __setitem__(self, turn, value):
        if type(value) is not FuturistWindowDict:
            value = FuturistWindowDict(value)
        super().__setitem__(turn, value)


class SettingsTurnDict(WindowDict):
    __slots__ = ('_future', '_past')
    cls = WindowDict

    def __getitem__(self, rev):
        try:
            return super().__getitem__(rev)
        except KeyError:
            ret = self[rev] = WindowDict()
            return ret

    def __setitem__(self, turn, value):
        if type(value) is not WindowDict:
            value = WindowDict(value)
        super().__setitem__(turn, value)


def _default_args_munger(self, k):
    return tuple()


def _default_kwargs_munger(self, k):
    return {}


class PickyDefaultDict(dict):
    """A ``defaultdict`` alternative that requires values of a specific type.

    Pass some type object (such as a class) to the constructor to
    specify what type to use by default, which is the only type I will
    accept.

    Default values are constructed with no arguments by default;
    supply ``args_munger`` and/or ``kwargs_munger`` to override this.
    They take arguments ``self`` and the unused key being looked up.

    """
    __slots__ = ['type', 'args_munger', 'kwargs_munger', 'parent', 'key']

    def __init__(
            self, type=object,
            args_munger=_default_args_munger,
            kwargs_munger=_default_kwargs_munger
    ):
        self.type = type
        self.args_munger = args_munger
        self.kwargs_munger = kwargs_munger

    def __getitem__(self, k):
        if k in self:
            return super(PickyDefaultDict, self).__getitem__(k)
        try:
            ret = self[k] = self.type(
                *self.args_munger(self, k),
                **self.kwargs_munger(self, k)
            )
        except TypeError:
            raise KeyError
        return ret

    def _create(self, v):
        return self.type(v)

    def __setitem__(self, k, v):
        if type(v) is not self.type:
            v = self._create(v)
        super(PickyDefaultDict, self).__setitem__(k, v)


class StructuredDefaultDict(dict):
    """A ``defaultdict``-like class that expects values stored at a specific depth.

    Requires an integer to tell it how many layers deep to go.
    The innermost layer will be ``PickyDefaultDict``, which will take the
    ``type``, ``args_munger``, and ``kwargs_munger`` arguments supplied
    to my constructor.

    """
    __slots__ = ['layer', 'type', 'args_munger', 'kwargs_munger', 'parent', 'key']

    def __init__(
            self, layers, type=object,
            args_munger=_default_args_munger,
            kwargs_munger=_default_kwargs_munger
    ):
        if layers < 1:
            raise ValueError("Not enough layers")
        self.layer = layers
        self.type = type
        self.args_munger = args_munger
        self.kwargs_munger = kwargs_munger

    def __getitem__(self, k):
        if k in self:
            return super(StructuredDefaultDict, self).__getitem__(k)
        if self.layer < 2:
            ret = PickyDefaultDict(
                self.type, self.args_munger, self.kwargs_munger
            )
        else:
            ret = StructuredDefaultDict(
                self.layer-1, self.type,
                self.args_munger, self.kwargs_munger
            )
        ret.parent = self
        ret.key = k
        super(StructuredDefaultDict, self).__setitem__(k, ret)
        return ret

    def __setitem__(self, k, v):
        if type(v) is StructuredDefaultDict:
            if (
                    v.layer == self.layer - 1
                    and v.type is self.type
                    and v.args_munger is self.args_munger
                    and v.kwargs_munger is self.kwargs_munger
            ):
                super().__setitem__(k, v)
                return
        elif type(v) is PickyDefaultDict:
            if (
                self.layer < 2
                and v.type is self.type
                and v.args_munger is self.args_munger
                and v.kwargs_munger is self.kwargs_munger
            ):
                super().__setitem__(k, v)
                return
        raise TypeError("Can't set layer {}".format(self.layer))


class Cache(object):
    """A data store that's useful for tracking graph revisions."""
    keycache_maxsize = 1024
    journal_container_cls = JournalContainer

    def __init__(self, db):
        self.db = db
        self.journal = self.journal_container_cls(db)
        self.keyframes = PickyDefaultDict(SettingsTurnDict)
        """Snapshots of my state at various times.
        
        Data prior to a keyframe may be unloaded if not in use.
        
        """
        self.loaded = {}
        """Tuples describing which parts of each branch are loaded.
        
        ``(earliest_turn, earliest_tick, latest_turn, latest_tick)``
        
        """
        self.parents = StructuredDefaultDict(3, TurnDict)
        """Entity data keyed by the entities' parents.

        An entity's parent is what it's contained in. When speaking of a node,
        this is its graph. When speaking of an edge, the parent is usually the
        graph and the origin in a pair, though for multigraphs the destination
        might be part of the parent as well.

        Deeper layers of this cache are keyed by branch and revision.

        """
        self.keys = StructuredDefaultDict(2, TurnDict)
        """Cache of entity data keyed by the entities themselves.

        That means the whole tuple identifying the entity is the
        top-level key in this cache here. The second-to-top level
        is the key within the entity.

        Deeper layers of this cache are keyed by branch, turn, and tick.

        """
        self.keycache = PickyDefaultDict(SettingsTurnDict)
        """Keys an entity has at a given turn and tick."""
        self.branches = StructuredDefaultDict(1, TurnDict)
        """A less structured alternative to ``keys``.

        For when you already know the entity and the key within it,
        but still need to iterate through history to find the value.

        """
        self.shallowest = OrderedDict()
        """A dictionary for plain, unstructured hinting."""
        self._kc_lru = OrderedDict()

    def load(self, data, validate=False, keyframe=False, cb=None):
        """Add a bunch of data. It doesn't need to be in chronological order.

        With ``validate=True``, raise ValueError if this results in an
        incoherent cache.

        If a callable ``cb`` is provided, it will be called with each row.
        It will also be passed my ``validate`` argument.

        """
        from collections import defaultdict, deque
        dd2 = defaultdict(lambda: defaultdict(list))
        for row in data:
            entity, key, branch, turn, tick, prev, value = row[-7:]
            dd2[branch][turn, tick].append(row)
        # Make keycaches and valcaches. Must be done chronologically
        # to make forwarding work.
        childbranch = self.db._childbranch
        branch2do = deque(['trunk'])
        if keyframe:
            # Even though we're still loading all the same data, putting it into
            # a keyframe rather than my special cache structures might be faster.
            # My cache structures are expensive to instantiate.
            # But all the same, it'd be better to save and load keyframes themselves.
            kftime = 'trunk', 0, 0
            kf = {}

            while branch2do:
                branch = branch2do.popleft()
                earliest_turn = earliest_tick = latest_turn = latest_tick = None
                dd2b = dd2[branch]
                # I think I could avoid sorting here
                for turn, tick in sorted(dd2b.keys()):
                    rows = dd2b[turn, tick]
                    for row in rows:
                        self.journal.store(*row)
                        kf[row[:-4]] = row[-1]
                        kftime = brnch, trn, tck = row[-4:-1]
                        if earliest_turn is None or (trn, tck) < (earliest_turn, earliest_tick):
                            (earliest_turn, earliest_tick) = (trn, tck)
                        if latest_turn is None or (trn, tck) > (latest_turn, latest_tick):
                            (latest_turn, latest_tick) = (trn, tck)
                        if cb:
                            cb(row, validate=validate)
                if branch in childbranch:
                    branch2do.extend(childbranch[branch])
                if None not in (earliest_turn, earliest_tick, latest_turn, latest_tick):
                    if branch in self.loaded:
                        earliest_turn2, earliest_tick2, latest_turn2, latest_tick2 \
                            = self.loaded[branch]
                        self.loaded[branch] = min((
                            (earliest_turn, earliest_tick), (earliest_turn2, earliest_tick2)
                        )) + max((
                            (latest_turn, latest_tick), (latest_turn2, latest_tick2)
                        ))
                    else:
                        self.loaded[branch] = earliest_turn, earliest_tick, latest_turn, latest_tick

            if not kf:
                return
            branch, turn, tick = kftime
            kfb = self.keyframes[branch]
            if turn in kfb:
                assert tick not in kfb[turn], "Already have a keyframe at {}, {}, {}".format(
                    branch, turn, tick
                )
            kfb[turn][tick] = kf
            return kf
        else:
            store = self._store
            while branch2do:
                branch = branch2do.popleft()
                earliest_turn = earliest_tick = latest_turn = latest_tick = None
                dd2b = dd2[branch]
                for turn, tick in sorted(dd2b.keys()):
                    if earliest_turn is None or (turn, tick) < (earliest_turn, earliest_tick):
                        (earliest_turn, earliest_tick) = (turn, tick)
                    if latest_turn is None or (turn, tick) > (latest_turn, latest_tick):
                        (latest_turn, latest_tick) = (turn, tick)
                    rows = dd2b[turn, tick]
                    for row in rows:
                        store(*row, planning=False, journal=True)
                        if cb:
                            cb(row, validate=validate)
                if branch in childbranch:
                    branch2do.extend(childbranch[branch])
                if None not in (earliest_turn, earliest_tick, latest_turn, latest_tick):
                    if branch in self.loaded:
                        earliest_turn2, earliest_tick2, latest_turn2, latest_tick2 \
                            = self.loaded[branch]
                        self.loaded[branch] = min((
                            (earliest_turn, earliest_tick), (earliest_turn2, earliest_tick2)
                        )) + max((
                            (latest_turn, latest_tick), (latest_turn2, latest_tick2)
                        ))
                    else:
                        self.loaded[branch] = earliest_turn, earliest_tick, latest_turn, latest_tick
            return dd2

    def unload(self, branch, turn, tick, direction='backward'):
        """Remove all data from before the time ``(turn, tick)`` in the given ``branch``.

        Or after that time, with ``direction='forward'``.

        """
        if direction not in {'forward', 'backward'}:
            raise ValueError("direction must be 'forward' or 'backward'")
        if branch in self.keyframes:
            trn, tck, _ = self.keyframes[branch]
            if (
                direction == 'forward' and (turn, tick) < (trn, tck)
            ) or (
                direction == 'backward' and (turn, tick) > (trn, tck)
            ):
                raise ValueError("Can't unload keyframe at {}".format((trn, tck)))
        # TODO: check if there's a keyframe sometime in the future when unloading backward
        # If there isn't, that whole branch subtree is unusable!
        earliest_turn, earliest_tick, latest_turn, latest_tick = self.loaded[branch]
        if (
            direction == 'backward' and (turn, tick) < (earliest_turn, earliest_tick)
        ) or (
            direction == 'forward' and (turn, tick) > (latest_turn, latest_tick)
        ):
            return
        keys = self.keys
        reverse = direction == 'backward'
        if turn == earliest_turn:
            mapps = [
                self.journal.settings[branch][turn],
                self.journal.presettings[branch][turn]
            ]
            for keysk in keys.values():
                if branch in keysk:
                    keyskb = keysk[branch]
                    if turn in keyskb:
                        mapps.append(keyskb[turn])
            for mapp in mapps:
                mapp.truncate(tick, reverse=reverse, inclusive=True)
        else:
            mapps = [
                self.journal.settings[branch],
                self.journal.presettings[branch]
            ]
            for keysk in keys.values():
                if branch in keysk:
                    mapps.append(keysk[branch])
            for mapp in mapps:
                if turn in mapp:
                    mappt = mapp[turn]
                    mappt.truncate(tick, reverse=reverse, inclusive=True)
                mapp.truncate(turn, reverse=reverse, inclusive=True)
        if reverse:
            self.loaded[branch] = turn, tick, latest_turn, latest_tick
        else:
            self.loaded[branch] = earliest_turn, earliest_tick, turn, tick

    def _valcache_lookup(self, cache, kfcache, branch, turn, tick):
        """Look up a value in a cache at a particular time.

        If, while travelling back in time, I encounter a keyframe in ``kfcache``,
        I'll return the value from it instead.

        """
        # why isn't this used in retrieve?
        if branch in kfcache and turn in kfcache[branch] and tick in kfcache[branch][turn]:
            return kfcache[branch][turn][tick][cache.key]
        if branch in cache:
            cacheb = cache[branch]
            if turn in cacheb:
                cachebt = cacheb[turn]
                if cachebt.rev_gettable(tick):
                    try:
                        return cachebt[tick]
                    except HistoryError as ex:
                        if ex.deleted:
                            return
                else:
                    try:
                        cachebt = cacheb[turn-1]
                        return cachebt[cachebt.end]
                    except HistoryError as ex:
                        if ex.deleted:
                            return
            elif cacheb.rev_gettable(turn):
                cachebt = cacheb[turn]
                try:
                    return cachebt[cachebt.end]
                except HistoryError as ex:
                    if ex.deleted:
                        return
        for b, r, t in self.db._iter_parent_btt(branch, turn, tick):
            if b in cache:
                cacheb = cache[b]
                if r in cacheb:
                    cachebr = cacheb[r]
                    if cachebr.rev_gettable(t):
                        return cachebr[t]
                    try:
                        cachebr = cacheb[r-1]
                        return cachebr[cachebr.end]
                    except HistoryError as ex:
                        if ex.deleted:
                            return
                elif cacheb.rev_gettable(r):
                    cachebr = cacheb[r]
                    try:
                        return cachebr[cachebr.end]
                    except HistoryError as ex:
                        if ex.deleted:
                            return
            if b in kfcache:
                kfcacheb = kfcache[b]
                if r in kfcacheb:
                    kfcachebr = kfcacheb[r]
                    if kfcachebr.rev_gettable(t):
                        return kfcachebr[t][cache.key]
                    elif kfcacheb.rev_gettable(r-1):
                        kfcachebr = kfcacheb[r-1]
                        return kfcachebr[kfcachebr.end][cache.key]
                elif kfcacheb.rev_gettable(r):
                    kfcachebr = kfcacheb[r]
                    return kfcachebr[kfcachebr.end][cache.key]

    def _get_keycachelike(self, keycache, keys, get_adds_dels, parentity, branch, turn, tick, *, forward):
        keycache_key = parentity + (branch,)
        if keycache_key in keycache and turn in keycache[keycache_key] and tick in keycache[keycache_key][turn]:
            return keycache[keycache_key][turn][tick]
        if forward:
            # Take valid values from the past of a keycache and copy them forward, into the present.
            # Assumes that time is only moving forward, never backward, never skipping any turns or ticks,
            # and any changes to the world state are happening through allegedb proper, meaning they'll all get cached.
            # In LiSE this means every change to the world state should happen inside of a call to
            # ``Engine.next_turn`` in a rule.
            if keycache_key in keycache and keycache[keycache_key].rev_gettable(turn):

                kc = keycache[keycache_key]
                if turn not in kc:
                    old_turn = kc.rev_before(turn)
                    old_turn_kc = kc[turn]
                    added, deleted = get_adds_dels(
                        keys[parentity], branch, turn, tick, stoptime=(
                            branch, old_turn, old_turn_kc.end
                        )
                    )
                    ret = old_turn_kc[old_turn_kc.end].union(added).difference(deleted)
                    # assert ret == get_adds_dels(keys[parentity], branch, turn, tick)[0]  # slow
                    new_turn_kc = WindowDict()
                    new_turn_kc[tick] = ret
                    kc[turn] = new_turn_kc
                    return ret
                kcturn = kc[turn]
                if tick not in kcturn:
                    if kcturn.rev_gettable(tick):
                        added, deleted = get_adds_dels(
                            keys[parentity], branch, turn, tick, stoptime=(
                                branch, turn, kcturn.rev_before(tick)
                            )
                        )
                        ret = kcturn[tick].union(added).difference(deleted)
                        # assert ret == get_adds_dels(keys[parentity], branch, turn, tick)[0]  # slow
                        kcturn[tick] = ret
                        return ret
                    else:
                        turn_before = kc.rev_before(turn)
                        tick_before = kc[turn_before].end
                        keys_before = kc[turn_before][tick_before]
                        added, deleted = get_adds_dels(
                            keys[parentity], branch, turn, tick, stoptime=(
                                branch, turn_before, tick_before
                            )
                        )
                        ret = kcturn[tick] = keys_before.union(added).difference(deleted)
                        # assert ret == get_adds_dels(keys[parentity], branch, turn, tick)[0]  # slow
                        return ret
                # assert kcturn[tick] == get_adds_dels(keys[parentity], branch, turn, tick)[0]  # slow
                return kcturn[tick]
            else:
                for (parbranch, parturn, partick) in self.db._iter_parent_btt(branch, turn, tick):
                    par_kc_key = parentity + (parbranch,)
                    if par_kc_key in keycache:
                        kcpkc = keycache[par_kc_key]
                        if parturn in kcpkc and kcpkc[parturn].rev_gettable(partick):
                            parkeys = kcpkc[parturn][partick]
                            break
                        elif kcpkc.rev_gettable(parturn-1):
                            partkeys = kcpkc[parturn-1]
                            parkeys = partkeys[partkeys.end]
                            break
                else:
                    parkeys = frozenset()
                kc = SettingsTurnDict()
                added, deleted = get_adds_dels(
                    keys[parentity], branch, turn, tick, stoptime=(
                        parbranch, parturn, partick
                    )
                )
                ret = parkeys.union(added).difference(deleted)
                kc[turn] = {tick: ret}
                keycache[keycache_key] = kc
                # assert ret == get_adds_dels(keys[parentity], branch, turn, tick)[0]  # slow
                return ret
        ret = frozenset(get_adds_dels(keys[parentity], branch, turn, tick)[0])
        if keycache_key in keycache:
            if turn in keycache[keycache_key]:
                keycache[keycache_key][turn][tick] = ret
            else:
                keycache[keycache_key][turn] = {tick: ret}
        else:
            kcc = SettingsTurnDict()
            kcc[turn][tick] = ret
            keycache[keycache_key] = kcc
        return ret

    def _get_keycache(self, parentity, branch, turn, tick, *, forward):
        self._lru_append(self.keycache, self._kc_lru, (parentity+(branch,), turn, tick), self.keycache_maxsize)
        return self._get_keycachelike(
            self.keycache, self.keys, self._get_adds_dels,
            parentity, branch, turn, tick, forward=forward
        )

    def _update_keycache(self, *args, forward):
        entity, key, branch, turn, tick, prev, value = args[-7:]
        parent = args[:-7]
        kc = self._get_keycache(parent + (entity,), branch, turn, tick, forward=forward)
        if value is None:
            kc = kc.difference((key,))
        else:
            kc = kc.union((key,))
        self.keycache[parent+(entity, branch)][turn][tick] = kc

    def _lru_append(self, kc, lru, kckey, maxsize):
        if kckey in lru:
            return
        while len(lru) >= maxsize:
            (peb, turn, tick), _ = lru.popitem(False)
            del kc[peb][turn][tick]
            if not kc[peb][turn]:
                del kc[peb][turn]
            if not kc[peb]:
                del kc[peb]
        lru[kckey] = True

    def _get_adds_dels(self, cache, branch, turn, tick, *, stoptime=None):
        added = set()
        deleted = set()
        for key, branches in cache.items():
            for (branc, trn, tck) in self.db._iter_parent_btt(branch, turn, tick, stoptime=stoptime):
                if branc not in branches or not branches[branc].rev_gettable(trn):
                    continue
                turnd = branches[branc]
                if trn in turnd:
                    if turnd[trn].rev_gettable(tck):
                        try:
                            if turnd[trn][tck] is not None:
                                added.add(key)
                                break
                        except HistoryError as ex:
                            if ex.deleted:
                                deleted.add(key)
                                break
                    else:
                        trn -= 1
                if not turnd.rev_gettable(trn):
                    break
                tickd = turnd[trn]
                try:
                    if tickd[tickd.end] is not None:
                        added.add(key)
                        break
                except HistoryError as ex:
                    if ex.deleted:
                        deleted.add(key)
                        break
        return added, deleted

    def store(self, *args, planning=None, forward=None):
        """Put a value in various dictionaries for later .retrieve(...).

        Needs at least five arguments, of which the -1th is the value
        to store, the -2th is the tick to store it at, the -3th
        is the turn to store it in, the -4th is the branch the
        revision is in, the -5th is the key the value is for,
        and the remaining arguments identify the entity that has
        the key, eg. a graph, node, or edge.

        With ``planning=True``, you will be permitted to alter
        "history" that takes place after the last non-planning
        moment of time, without much regard to consistency.
        Otherwise, contradictions will be handled by deleting
        everything after the present moment.

        """
        if planning is None:
            planning = self.db._planning
        if forward is None:
            forward = self.db._forward
        self._store(*args, planning=planning, journal=True)
        if not self.db._no_kc:
            self._update_keycache(*args, forward=forward)

    def _store(self, *args, planning, journal):
        entity, key, branch, turn, tick, prev, value = args[-7:]
        parent = args[:-7]
        if branch in self.loaded:
            early_turn, early_tick, late_turn, late_tick = self.loaded[branch]
        else:
            early_turn, early_tick = late_turn, late_tick = turn, tick
        if turn < early_turn:
            early_turn, early_tick = turn, tick
        elif turn > late_turn:
            late_turn, late_tick = turn, tick
        elif turn == early_turn:
            if tick < early_tick:
                early_tick = tick
        elif turn == late_turn:
            if tick > late_tick:
                late_tick = tick
        self.loaded[branch] = early_turn, early_tick, late_turn, late_tick
        if parent:
            parentity = self.parents[parent][entity]
            if key in parentity:
                branches = parentity[key]
                assert branches is self.branches[parent+(entity, key)] is self.keys[parent+(entity,)][key]
                turns = branches[branch]
            else:
                branches = self.branches[parent+(entity, key)] \
                    = self.keys[parent+(entity,)][key] \
                    = parentity[key]
                turns = branches[branch]
        else:
            if (entity, key) in self.branches:
                branches = self.branches[entity, key]
                assert branches is self.keys[entity, ][key]
                turns = branches[branch]
            else:
                branches = self.branches[entity, key]
                self.keys[entity,][key] = branches
                turns = branches[branch]
        if planning:
            if turn in turns and tick < turns[turn].end:
                raise HistoryError(
                    "Already have some ticks after {} in turn {} of branch {}".format(
                        tick, turn, branch
                    )
                )
        else:
            # truncate settings
            self.journal.truncate(branch, turn, tick)
            if turn in turns:
                turns[turn].truncate(tick)
            turns.truncate(turn)
        if journal:
            self.journal.store(*args)
        self.shallowest[parent+(entity, key, branch, turn, tick)] = value
        while len(self.shallowest) > self.keycache_maxsize:
            self.shallowest.popitem(False)
        if turn in turns:
            the_turn = turns[turn]
            the_turn.truncate(tick)
            the_turn[tick] = value
        else:
            new = FuturistWindowDict()
            new[tick] = value
            turns[turn] = new
        if branch in self.loaded:
            earliest_turn, earliest_tick, latest_turn, latest_tick = self.loaded[branch]
            self.loaded[branch] = min((
                (earliest_turn, earliest_tick), (turn, tick)
            )) + max((
                (latest_turn, latest_tick), (turn, tick)
            ))
        else:
            self.loaded[branch] = turn, tick, turn, tick

    def _check_loaded(self, branch, turn, tick):
        if branch in self.loaded:
            earliest_turn, earliest_tick, latest_turn, latest_tick = self.loaded[branch]
            if (turn, tick) < (earliest_turn, earliest_tick):
                raise UnloadedException(
                    branch, turn, tick,
                    "The time {} is not loaded within the branch {}".format(
                        (turn, tick), branch
                    ))
        else:
            raise UnloadedException(
                branch, None, None,
                "The branch {} is not loaded".format(branch)
            )

    def retrieve(self, *args):
        """Get a value previously .store(...)'d.

        Needs at least five arguments. The -1th is the tick
        within the turn you want,
        the -2th is that turn, the -3th is the branch,
        and the -4th is the key. All other arguments identify
        the entity that the key is in.

        """
        shallowest = self.shallowest
        try:
            ret = shallowest[args]
            if ret is None:
                raise HistoryError("Set, then deleted", deleted=True)
            return ret
        except HistoryError:
            raise
        except KeyError:
            pass
        entity = args[:-4]
        key, branch, turn, tick = args[-4:]
        check_loaded = self._check_loaded
        check_loaded(branch, turn, tick)
        branches = self.branches
        if entity+(key,) in branches:
            if (
                branch in branches[entity+(key,)]
                and branches[entity+(key,)][branch].rev_gettable(turn)
            ):
                brancs = branches[entity+(key,)][branch]
                if turn in brancs:
                    if brancs[turn].rev_gettable(tick):
                        ret = brancs[turn][tick]
                        shallowest[args] = ret
                        return ret
                    elif brancs.rev_gettable(turn-1):
                        b1 = brancs[turn-1]
                        ret = b1[b1.end]
                        shallowest[args] = ret
                        return ret
                else:
                    ret = brancs[turn]
                    ret = ret[ret.end]
                    shallowest[args] = ret
                    return ret
        keyframes = self.keyframes
        # TODO: if there's a keyframe in this branch in the future, use it.
        for (b, r, t) in self.db._iter_parent_btt(branch):
            check_loaded(b, r, t)
            if entity+(key,) in branches:
                if (
                        b in branches[entity+(key,)]
                        and branches[entity+(key,)][b].rev_gettable(r)
                ):
                    brancs = branches[entity+(key,)][b]
                    if r in brancs and brancs[r].rev_gettable(t):
                        ret = shallowest[args] = brancs[r][t]
                        return ret
                    elif brancs.rev_gettable(r-1):
                        ret = brancs[r-1]
                        ret = shallowest[args] = ret[ret.end]
                        return ret
            if b in keyframes:
                trn, tck, kf = keyframes[b]
                if r > trn or (r == trn and t >= tck):
                    # may raise KeyError
                    ret = shallowest[args] = kf[entity + (key,)]
                    return ret
                else:
                    continue
        else:
            raise KeyError

    def iter_entities_or_keys(self, *args, forward=None):
        """Iterate over the keys an entity has, if you specify an entity.

        Otherwise iterate over the entities themselves, or at any rate the
        tuple specifying which entity.

        """
        if forward is None:
            forward = self.db._forward
        entity = args[:-3]
        branch, turn, tick = args[-3:]
        if self.db._no_kc:
            yield from self._get_adds_dels(self.keys[entity], branch, turn, tick)[0]
            return
        yield from self._get_keycache(entity, branch, turn, tick, forward=forward)
    iter_entities = iter_keys = iter_entity_keys = iter_entities_or_keys

    def count_entities_or_keys(self, *args, forward=None):
        """Return the number of keys an entity has, if you specify an entity.

        Otherwise return the number of entities.

        """
        if forward is None:
            forward = self.db._forward
        entity = args[:-3]
        branch, turn, tick = args[-3:]
        if self.db._no_kc:
            return len(self._get_adds_dels(self.keys[entity], branch, turn, tick)[0])
        return len(self._get_keycache(entity, branch, turn, tick, forward=forward))
    count_entities = count_keys = count_entity_keys = count_entities_or_keys

    def contains_entity_or_key(self, *args):
        """Check if an entity has a key at the given time, if entity specified.

        Otherwise check if the entity exists.

        """
        try:
            return self.retrieve(*args) is not None
        except KeyError:
            return False
    contains_entity = contains_key = contains_entity_key \
                    = contains_entity_or_key


class NodesCache(Cache):
    """A cache for remembering whether nodes exist at a given time."""

    def store(self, graph, node, branch, turn, tick, ex, *, planning=None, forward=None):
        return super().store(graph, node, branch, turn, tick, not ex, ex or None, planning=planning, forward=forward)


class EdgesCache(Cache):
    """A cache for remembering whether edges exist at a given time."""
    @property
    def successors(self):
        return self.parents

    def __init__(self, db):
        Cache.__init__(self, db)
        self.destcache = PickyDefaultDict(SettingsTurnDict)
        self.origcache = PickyDefaultDict(SettingsTurnDict)
        self.predecessors = StructuredDefaultDict(3, TurnDict)
        self._origcache_lru = OrderedDict()
        self._destcache_lru = OrderedDict()

    def _adds_dels_sucpred(self, cache, branch, turn, tick, *, stoptime=None):
        added = set()
        deleted = set()
        for node, nodes in cache.items():
            addidx, delidx = self._get_adds_dels(nodes, branch, turn, tick, stoptime=stoptime)
            if addidx:
                assert not delidx
                added.add(node)
            elif delidx:
                assert delidx and not addidx
                deleted.add(node)
        return added, deleted

    def _get_destcache(self, graph, orig, branch, turn, tick, *, forward):
        self._lru_append(self.destcache, self._destcache_lru, ((graph, orig, branch), turn, tick), self.keycache_maxsize)
        return self._get_keycachelike(
            self.destcache, self.successors, self._adds_dels_sucpred, (graph, orig),
            branch, turn, tick, forward=forward
        )

    def _get_origcache(self, graph, dest, branch, turn, tick, *, forward):
        self._lru_append(self.origcache, self._origcache_lru, ((graph, dest, branch), turn, tick), self.keycache_maxsize)
        return self._get_keycachelike(
            self.origcache, self.predecessors, self._adds_dels_sucpred, (graph, dest),
            branch, turn, tick, forward=forward
        )

    def iter_successors(self, graph, orig, branch, turn, tick, *, forward=None):
        """Iterate over successors of a given origin node at a given time."""
        if self.db._no_kc:
            yield from self._adds_dels_sucpred(self.successors[graph, orig], branch, turn, tick)[0]
            return
        if forward is None:
            forward = self.db._forward
        yield from self._get_destcache(graph, orig, branch, turn, tick, forward=forward)

    def iter_predecessors(self, graph, dest, branch, turn, tick, *, forward=None):
        """Iterate over predecessors to a given destination node at a given time."""
        if self.db._no_kc:
            yield from self._adds_dels_sucpred(self.predecessors[graph, dest], branch, turn, tick)[0]
            return
        if forward is None:
            forward = self.db._forward
        yield from self._get_origcache(graph, dest, branch, turn, tick, forward=forward)

    def count_successors(self, graph, orig, branch, turn, tick, *, forward=None):
        """Return the number of successors to a given origin node at a given time."""
        if self.db._no_kc:
            return len(self._adds_dels_sucpred(self.successors[graph, orig], branch, turn, tick)[0])
        if forward is None:
            forward = self.db._forward
        return len(self._get_destcache(graph, orig, branch, turn, tick, forward=forward))

    def count_predecessors(self, graph, dest, branch, turn, tick, *, forward=None):
        """Return the number of predecessors from a given destination node at a given time."""
        if self.db._no_kc:
            return len(self._adds_dels_sucpred(self.predecessors[graph, dest], branch, turn, tick)[0])
        if forward is None:
            forward = self.db._forward
        return len(self._get_origcache(graph, dest, branch, turn, tick, forward=forward))

    def has_successor(self, graph, orig, dest, branch, turn, tick):
        """Return whether an edge connects the origin to the destination at the given time."""
        try:
            return self.retrieve(graph, orig, dest, 0, branch, turn, tick) is not None
        except KeyError:
            return False

    def has_predecessor(self, graph, dest, orig, branch, turn, tick):
        """Return whether an edge connects the destination to the origin at the given time."""
        try:
            return self.retrieve(graph, orig, dest, 0, branch, turn, tick) is not None
        except KeyError:
            return False

    def store(self, graph, orig, dest, idx, branch, turn, tick, ex, *, planning=None, forward=None):
        super().store(graph, orig, dest, idx, branch, turn, tick, not ex, ex, planning=planning, forward=forward)

    def _store(self, graph, orig, dest, idx, branch, turn, tick, prev, ex, *, planning, journal):
        if prev == ex:
            return
        Cache._store(self, graph, orig, dest, idx, branch, turn, tick, prev, ex or None,
                     planning=planning, journal=journal)
        self.predecessors[(graph, dest)][orig][idx][branch][turn] \
            = self.successors[graph, orig][dest][idx][branch][turn]
        if ex:
            assert self.has_successor(graph, orig, dest, branch, turn, tick)
            assert self.has_predecessor(graph, dest, orig, branch, turn, tick)


class DataSwapper:
    """Gets and sets data, caching as needed."""
    def __init__(self, cache, saver, loader):
        self.cache = cache
        self.saver = saver
        self.loader = loader

    def store(self, *args, planning=None, forward=None):
        self.saver(*args)
        self.cache.store(*args, planning=planning, forward=forward)

    def retrieve(self, *args):
        try:
            return self.cache.retrieve(*args)
        except UnloadedException:
            self.load(*args[-3:])
            return self.cache.retrieve(*args)

    def load(self, branch, turn, tick):
        raise NotImplementedError

    def iter_entities_or_keys(self, *args, forward=None):
        __doc__ = Cache.iter_entities_or_keys.__doc__
        try:
            return self.cache.iter_entities_or_keys(*args, forward=forward)
        except UnloadedException:
            self.load(*args[-3])  # actually expand the window of what's loaded
            return self.cache.iter_entities_or_keys(*args, forward=forward)
    iter_entities = iter_keys = iter_entities_or_keys

    def count_entities_or_keys(self, *args, forward=None):
        __doc__ = Cache.count_entities_or_keys.__doc__
        return self.cache.count_entities_or_keys(*args, forward=forward)
    count_entities = count_keys = count_entities_or_keys


class EdgesDataSwapper(DataSwapper):
    def iter_successors(self, graph, orig, branch, turn, tick, *, forward=None):
        __doc__ = EdgesCache.iter_successors.__doc__
        return self.cache.iter_successors(graph, orig, branch, turn, tick, forward=forward)

    def iter_predecessors(self, graph, dest, branch, turn, tick, *, forward=None):
        __doc__ = EdgesCache.iter_predecessors.__doc__
        return self.cache.iter_predecessors(graph, dest, branch, turn, tick, forward=forward)

    def count_successors(self, graph, orig, branch, turn, tick, *, forward=None):
        __doc__ = EdgesCache.count_successors.__doc__
        return self.cache.count_successors(graph, orig, branch, turn, tick, forward=forward)

    def count_predecessors(self, graph, dest, branch, turn, tick, *, forward=None):
        __doc__ = EdgesCache.count_predecessors.__doc__
        return self.cache.count_predecessors(graph, dest, branch, turn, tick, forward=forward)

    def has_successor(self, graph, orig, dest, branch, turn, tick):
        __doc__ = EdgesCache.has_successor.__doc__
        return self.cache.has_successor(graph, orig, dest, branch, turn, tick)

    def has_predecessor(self, graph, dest, orig, branch, turn, tick):
        __doc__ = EdgesCache.has_predecessor.__doc__
        return self.cache.has_predecessor(graph, dest, orig, branch, turn, tick)