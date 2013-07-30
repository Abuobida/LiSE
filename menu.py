from util import SaveableMetaclass, dictify_row
import re
import pyglet


"""Simple menu widgets"""


__metaclass__ = SaveableMetaclass


ON_CLICK_RE = re.compile("""([a-zA-Z0-9_]+)\((.*)\)""")


class MenuItem:
    """A thing in a menu that you can click to make something happen."""
    tables = [
        ('menu_item',
         {"window": "text not null default 'Main'",
          'menu': 'text not null',
          'idx': 'integer not null',
          'text': 'text not null',
          'on_click': 'text not null',
          'closer': "boolean not null default 1"},
         ("window", "menu", "idx"),
         {"window, menu": ("menu", "window, name")},
         [])]
    visible = True
    interactive = True

    def __init__(self, menu, idx, text, closer, on_click_fun, on_click_arg_str, on_click_arg_re):
        """Return a menu item in the given board, the given menu; at the given
index in that menu; with the given text; which executes the given
effect deck when clicked; closes or doesn't when clicked; starts
visible or doesn't; and starts interactive or doesn't.

With db, register in db's menuitemdict.

        """
        self.db = menu.db
        self.menu = menu
        self.window = self.menu.window
        self.idx = idx
        self._text = text
        try:
            on_click_arg_tup = re.match(on_click_arg_re, on_click_arg_str).groups()
        except:
            on_click_arg_tup = tuple()
        def on_click(self):
            t = (self,) + on_click_arg_tup
            return on_click_fun(*t)
        self.on_click = on_click
        self.closer = closer
        self.grabpoint = None
        self.label = None
        self.oldstate = None
        self.newstate = None
        self.pressed = False
        self.tweaks = 0

    def __int__(self):
        return self.idx

    def __getattr__(self, attrn):
        if attrn == 'text':
            if self._text[0] == '@':
                return self.db.get_text(self._text[1:])
            else:
                return self._text
        elif attrn == 'hovered':
            return self.window.hovered is self
        elif attrn == 'pressed':
            return self.window.pressed is self
        elif attrn == 'window_left':
            return self.menu.window_left + self.menu.style.spacing
        elif attrn == 'window_right':
            return self.menu.window_right - self.menu.style.spacing
        elif attrn == 'width':
            return self.window_right - self.window_left
        elif attrn == 'height':
            return self.window_top - self.window_bot
        elif attrn == 'rx':
            return self.width / 2
        elif attrn == 'ry':
            return self.height / 2
        elif attrn == 'r':
            if self.rx > self.ry:
                return self.rx
            else:
                return self.ry
        else:
            raise AttributeError(
                "MenuItem instance has no such attribute: " +
                attrn)

    def __eq__(self, other):
        """Compare the menu and the idx to see if these menu items ought to be
the same."""
        return (
            isinstance(other, MenuItem) and
            self.menu == other.menu and
            self.idx == other.idx)

    def __gt__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text > other
        return self.text > other.text

    def __ge__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text >= other
        return self.text >= other.text

    def __lt__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text < other
        return self.text < other.text

    def __le__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text <= other
        return self.text <= other.text

    def __repr__(self):
        """Show my text"""
        return self.text

    def onclick(self):
        return self.on_click(self)

    def toggle_visibility(self):
        """Become visible if invisible or vice versa"""
        self.visible = not self.visible
        self.tweaks += 1

    def hide(self):
        """Become invisible"""
        if self.visible:
            self.toggle_visibility()

    def show(self):
        """Become visible"""
        if not self.visible:
            self.toggle_visibility()

    def get_state_tup(self):
        """Return a tuple containing everything that's relevant to deciding
just how to display this widget"""
        return (
            hash(self.menu.get_state_tup()),
            self.idx,
            self.text,
            self.visible,
            self.interactive,
            self.grabpoint,
            self.pressed,
            self.tweaks)

    def get_tabdict(self):
        return {
            "menu_item": [{
                "board": str(self.board),
                "menu": str(self.menu),
                "idx": self.idx,
                "text": self._text,
                "on_click": self.on_click,
                "closer": self.closer}]
        }

    def delete(self):
        del self.db.menuitemdict[self._board][self._menu][self.idx]
        self.erase()


class Menu:
    """Container for MenuItems; not interactive unto itself."""
    tables = [
        ('menu',
         {"window": "text not null default 'Main'",
          'name': 'text not null',
          'left': "float not null default 0.1",
          'bottom': "float not null default 0.0",
          'top': 'float not null default 1.0',
          'right': 'float not null default 0.2',
          'style': "text not null default 'SmallDark'"},
         ("window", 'name'),
         {"window": ("window", "name"),
          "style": ("style", "name")},
         [])]
    interactive = True

    def __init__(self, window, name, left, bottom, top, right, style):
        """Return a menu in the given board, with the given name, bounds,
style, and flags main_for_window and visible.

Bounds are proportional with respect to the lower left corner of the
window. That is, they are floats, never below 0.0 nor above 1.0, and
they express a portion of the window's width or height.

main_for_window prevents the menu from ever being hidden. visible
determines if you can see it at the moment.

With db, register with db's menudict.

        """
        self.window = window
        self.board = self.window.board
        self.db = self.board.db
        self.name = name
        self.left_prop = left
        self.bot_prop = bottom
        self.top_prop = top
        self.right_prop = right
        self.style = style
        self.active_pattern = pyglet.image.SolidColorImagePattern(
            self.style.bg_active.tup)
        self.inactive_pattern = pyglet.image.SolidColorImagePattern(
            self.style.bg_inactive.tup)
        self.rowheight = self.style.fontsize + self.style.spacing
        self.items = []
        self.visible = False
        self.grabpoint = None
        self.sprite = None
        self.oldstate = None
        self.newstate = None
        self.pressed = False
        self.freshly_adjusted = False
        self.tweaks = 0

    def __str__(self):
        return self.name

    def __getattr__(self, attrn):
        if attrn == 'hovered':
            return self.window.hovered is self
        elif attrn == 'window_left':
            if self.window is None:
                return 0
            else:
                return int(self.window.width * self.left_prop)
        elif attrn == 'window_bot':
            if self.window is None:
                return 0
            else:
                return int(self.window.height * self.bot_prop)
        elif attrn == 'window_top':
            if self.window is None:
                return 0
            else:
                return int(self.window.height * self.top_prop)
        elif attrn == 'window_right':
            if self.window is None:
                return 0
            else:
                return int(self.window.width * self.right_prop)
        elif attrn == 'width':
            return self.window_right - self.window_left
        elif attrn == 'height':
            return self.window_top - self.window_bot
        elif attrn == 'rx':
            return int(
                (self.window.width * self.right_prop -
                 self.window.width * self.left_prop)
                / 2)
        elif attrn == 'ry':
            return int(
                (self.window.height * self.top_prop -
                 self.window.height * self.bot_prop)
                / 2)
        elif attrn == 'r':
            if self.rx > self.ry:
                return self.rx
            else:
                return self.ry
        else:
            raise AttributeError(
                "Menu instance has no such attribute: " +
                attrn)

    def __eq__(self, other):
        """Return true if the names and boards match"""
        return (
            self.name == other.name and
            self.board == other.board)

    def __getitem__(self, i):
        """Return an item herein"""
        return self.items[i]

    def __setitem__(self, i, to):
        """Set a menuitem"""
        self.items[i] = to

    def __delitem__(self, i):
        """Delete a menuitem"""
        return self.items.__delitem__(i)

    def __contains__(self, mi):
        return mi in self.items

    def append(self, mi):
        self.items.append(mi)

    def remove(self, mi):
        self.items.remove(mi)

    def index(self, mi):
        return self.items.index(mi)

    def adjust(self):
        """Assign absolute coordinates to myself and all my items."""
        i = 0
        for item in self.items:
            item.top_from_top = i * self.rowheight
            item.bot_from_top = item.top_from_top + self.rowheight
            item.window_top = self.window_top - item.top_from_top
            item.window_bot = item.window_top - self.rowheight
            i += 1

    def get_state_tup(self):
        """Return a tuple containing everything you need to decide how to draw
me"""
        return (
            self,
            self.window_left,
            self.window_bot,
            self.window_top,
            self.window_right,
            self.style,
            self.visible,
            self.grabpoint,
            self.pressed,
            self.tweaks)

    def get_tabdict(self):
        return {
            "menu": [{
                "board": str(self.board),
                "name": str(self),
                "left": self.left_prop,
                "bottom": self.bot_prop,
                "top": self.top_prop,
                "right": self.right_prop,
                "style": str(self.style),
                "main_for_window": self.main_for_window}]
        }

    def save(self):
        for it in self.items:
            it.save()
        self.coresave()
