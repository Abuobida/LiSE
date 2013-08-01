from util import SaveableMetaclass


"""Things that should have character sheets."""


__metaclass__ = SaveableMetaclass


class Character:
    """An incorporeal object connecting corporeal ones together across
dimensions, indicating that they represent one thing and have that
thing's attributes.

Every item in LiSE's world model must be part of a Character, though
it may be the only member of that Character. Where items can only have
generic attributes appropriate to the dimension they occupy,
Characters have all the attributes of the items that make them up, and
possibly many more. There are no particular restrictions on what
manner of attribute a Character can have, so long as it is not used by
the physics of any dimension.

Characters may contain EventDecks. These may represent skills the
character has, in which case every EventCard in the EventDeck
represents something can happen upon using the skill, regardless of
what it's used on or where. "Success" and "failure" are appropriate
EventCards in this case, though there may be finer distinctions to be
made between various kinds of success and failure with a given skill.

However, the EventCards that go in a Character's EventDeck to
represent a skill should never represent anything particular to any
use-case of the skill. Those EventCards should instead be in the
EventDeck of those other Characters--perhaps people, perhaps places,
perhaps tools--that the skill may be used on, with, or for. All of
those Characters' relevant EventDecks will be used in constructing a
new one, called the OutcomeDeck, and the outcome of the event will be
drawn from that.

Otherwise, Characters can be treated much like three-dimensional
dictionaries, wherein you may look up the Character's attributes. The
key is composed of the dimension an item of this character is in, the
item's name, and the name of the attribute.

"""
    tables = [
        ("character_things",
         {"character": "text not null",
          "dimension": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "thing": "text not null"},
         ("character", "dimension", "thing", "branch", "tick_from"),
         {"dimension, thing": ("thing", "dimension, name")},
         []),
        ("character_skills",
         {"character": "text not null",
          "skill": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "effect_deck": "text not null"},
         ("character", "skill", "branch", "tick_from"),
         {"effect_deck": ("effect_deck", "name")},
         []),
        ("character_attributions",
         {"character": "text not null",
          "attribute": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "value": "text not null"},
         ("character", "attribute", "branch", "tick_from"),
         {},
         [])]

    def __init__(self, db, name):
        self.name = name
        self.db = db
        self.thingdict = {}
        self.indefinite_thing = {}
        self.skilldict = {}
        self.indefinite_skill = {}
        self.attribdict = {}
        self.indefinite_attrib = {}

    def set_attrib(self, trib, val, branch=None, tick_from=None, tick_to=None):
        if branch is None:
            branch = self.db.branch
        if tick_from is None:
            tick_from = self.db.tick
        if branch not in self.attribdict:
            self.attribdict[branch] = {}
        if trib not in self.attribdict[branch]:
            self.attribdict[branch][trib] = {}
        if branch in self.indefinite_attrib and trib in self.indefinite_attrib[branch]:
            ifrom = self.indefinite_attrib[branch][trib]
            (ival, ito) = self.attribdict[branch][ifrom][trib]
            if tick_from > ifrom:
                self.attribdict[branch][trib][ifrom] = (ival, tick_from - 1)
                del self.indefinite_attrib[branch][trib]
            elif tick_from == ifrom or tick_to > ifrom:
                del self.attribdict[branch][trib][ifrom]
                del self.indefinite_attrib[branch][trib]
        self.attribdict[branch][trib][tick_from] = (val, tick_to)
        if tick_to is None:
            if branch not in self.indefinite_attrib:
                self.indefinite_attrib[branch] = {}
            self.indefinite_attrib[branch][trib] = tick_from

    def get_attrib(self, trib, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.attribdict:
            return None
        for (tick_from, (val, tick_to)) in self.attribdict[branch].iterthings():
            if tick_from <= tick and (tick_to is None or tick <= tick_to):
                return val
        return None

    def set_skill(self, skill, val, branch=None, tick_from=None, tick_to=None):
        if branch is None:
            branch = self.db.branch
        if tick_from is None:
            tick_from = self.db.tick
        if branch not in self.skilldict:
            self.skilldict[branch] = {}
        if skill not in self.skilldict[branch]:
            self.skilldict[branch][skill] = {}
        if branch in self.indefinite_skill and skill in self.indefinite_skill[branch]:
            ifrom = self.indefinite_skill[branch][skill]
            (ival, ito) = self.skilldict[branch][skill][ifrom]
            if tick_from > ifrom:
                self.skilldict[branch][skill][ifrom] = (ival, tick_from - 1)
                del self.indefinite_skill[branch][skill]
            elif tick_from == ifrom or tick_to > ifrom:
                del self.skilldict[branch][skill][ifrom]
                del self.indefinite_skill[branch][skill]
        self.skilldict[branch][skill][tick_from] = (val, tick_to)
        if tick_to is None:
            if branch not in self.indefinite_skill:
                self.indefinite_skill[branch] = {}
            self.indefinite_skill[branch][skill] = tick_from

    def get_skill(self, skill, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.skilldict:
            return None
        for (tick_from, (val, tick_to)) in self.skilldict[branch].iterthings():
            if tick_from <= tick and (tick_to is None or tick <= tick_to):
                return val
        return None

    def add_thing_with_strs(self, dimn, thingn, branch=None, tick_from=None, tick_to=None):
        if branch is None:
            branch = self.db.branch
        if tick_from is None:
            tick_from = self.db.tick
        if branch not in self.thingdict:
            self.thingdict[branch] = {}
        if dimn not in self.thingdict[branch]:
            self.thingdict[branch][dimn] = {}
        if thingn not in self.thingdict[branch][dimn]:
            self.thingdict[branch][dimn][thingn] = {}
        if (
                branch in self.indefinite_thing and
                dimn in self.indefinite_thing[branch] and
                thingn in self.indefinite_thing[branch][dimn]):
            ifrom = self.indefinite_thing[branch][dimn][thingn]
            if tick_from > ifrom:
                self.thingdict[branch][dimn][thingn][ifrom] = tick_from - 1
                del self.indefinite_thing[branch][dimn][thingn]
            elif tick_from == ifrom or tick_to > ifrom:
                del self.thingdict[branch][dimn][thingn][ifrom]
                del self.indefinite_thing[branch][dimn][thingn]
        self.thingdict[branch][dimn][thingn][tick_from] = tick_to
        if tick_to is None:
            if branch not in self.indefinite_thing:
                self.indefinite_thing[branch] = {}
            if dimn not in self.indefinite_thing[branch]:
                self.indefinite_thing[branch][dimn] = {}
            self.indefinite_thing[branch][dimn][thingn] = tick_from

    def add_thing(self, thing, branch=None, tick=None):
        dimn = str(thing.dimension)
        thingn = str(thing)
        self.add_thing_with_strs(dimn, thingn, branch, tick)

    def is_thing_with_strs(self, dimn, thingn, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if not (
                branch in self.thingdict and
                dimn in self.thingdict[branch] and
                thingn in self.thingdict[branch][dimn]):
            return False
        for (tick_from, tick_to) in self.thingdict[branch][dimn][thingn].iteritems():
            if tick_from <= tick and (tick_to is None or tick <= tick_to):
                return True
        return False

    def is_thing(self, thing, branch=None, tick=None):
        dimn = str(thing.dimension)
        thingn = str(thing)
        return self.is_thing_with_strs(dimn, thingn, branch, tick)

    def get_things(self, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        r = set()
        if branch not in self.thingdict:
            return r
        for (dimn, thingsd) in self.thingdict[branch].iteritems():
            for (thingn, ticksd) in thingsd.iteritems():
                for (tick_from, tick_to) in ticksd.iteritems():
                    if tick_from <= tick and (
                            tick_to is None or tick <= tick_to):
                        dim = self.db.dimensiondict[dimn]
                        thing = dim.things_by_name[thingn]
                        r.add(thing)
        return r

    def get_tabdict(self):
        things = [
            {"character": self.name,
             "dimension": it.dimension.name,
             "thing": it.name}
            for it in iter(self.things)]
        skills = [
            {"character": self.name,
             "skill": sk.name,
             "effect_deck": sk.effect_deck.name}
            for sk in iter(self.skills)]
        attributions = [
            {"character": self.name,
             "attribute": thing[0],
             "value": thing[1]}
            for thing in self.attributions]
        return {
            "character_thing_link": things,
            "character_skill_link": skills,
            "attribution": attributions}

    def get_keydict(self):
        things = [
            {"character": str(self),
             "dimension": str(it.dimension),
             "thing": it.name}
            for it in iter(self.things)]
        skills = [
            {"character": str(self),
             "skill": str(self)}
            for sk in iter(self.skills)]
        attributions = [
            {"character": self.name,
             "attribute": att}
            for (att, val) in iter(self.attributions)]
        return {
            "character_thing_link": things,
            "character_skill_link": skills,
            "attribution": attributions}

    def delete(self):
        del self.db.characterdict[self.name]
        self.erase()

    def unravel(self):
        pass
