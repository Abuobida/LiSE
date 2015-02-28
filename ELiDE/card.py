# This file is part of LiSE, a framework for life simulation games.
# Copyright (C) 2013-2014 Zachary Spector, ZacharySpector@gmail.com
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import (
    AliasProperty,
    BooleanProperty,
    DictProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    OptionProperty,
    ReferenceListProperty,
    StringProperty,
    BoundedNumericProperty
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.layout import Layout
from kivy.uix.stencilview import StencilView
from kivy.uix.image import Image
from kivy.uix.widget import Widget


def get_pos_hint_x(poshints, sizehintx):
    if 'x' in poshints:
        return poshints['x']
    elif sizehintx is not None:
        if 'center_x' in poshints:
            return (
                poshints['center_x'] -
                sizehintx / 2
            )
        elif 'right' in poshints:
            return (
                poshints['right'] -
                sizehintx
            )


def get_pos_hint_y(poshints, sizehinty):
    if 'y' in poshints:
        return poshints['y']
    elif sizehinty is not None:
        if 'center_y' in poshints:
            return (
                poshints['center_y'] -
                sizehinty / 2
            )
        elif 'top' in poshints:
            return (
                poshints['top'] -
                sizehinty
            )


def get_pos_hint(poshints, sizehintx, sizehinty):
    return (
        get_pos_hint_x(poshints, sizehintx),
        get_pos_hint_y(poshints, sizehinty)
    )


class ColorTextureBox(Widget):
    color = ListProperty([1, 1, 1, 1])
    outline_color = ListProperty([0, 0, 0, 0])
    texture = ObjectProperty(None, allownone=True)


class Card(FloatLayout):
    dragging = BooleanProperty(False)
    deck = NumericProperty()
    idx = NumericProperty()
    ud = DictProperty({})

    collide_x = NumericProperty()
    collide_y = NumericProperty()
    collide_pos = ReferenceListProperty(collide_x, collide_y)

    foreground = ObjectProperty()
    foreground_source = StringProperty('')
    foreground_color = ListProperty([1, 1, 1, 1])
    foreground_image = ObjectProperty(None, allownone=True)
    foreground_texture = ObjectProperty(None, allownone=True)

    background_source = StringProperty('')
    background_color = ListProperty([.7, .7, .7, 1])
    background_image = ObjectProperty(None, allownone=True)
    background_texture = ObjectProperty(None, allownone=True)

    outline_color = ListProperty([0, 0, 0, 1])
    content_outline_color = ListProperty([0, 0, 0, 0])
    foreground_outline_color = ListProperty([0, 0, 0, 1])
    art_outline_color = ListProperty([0, 0, 0, 0])

    art = ObjectProperty()
    art_source = StringProperty('')
    art_color = ListProperty([1, 1, 1, 1])
    art_image = ObjectProperty(None, allownone=True)
    art_texture = ObjectProperty(None, allownone=True)
    show_art = BooleanProperty(True)

    headline = ObjectProperty()
    headline_text = StringProperty('Headline')
    headline_markup = BooleanProperty(True)
    headline_font_name = StringProperty('DroidSans')
    headline_font_size = NumericProperty(18)
    headline_color = ListProperty([0, 0, 0, 1])

    midline = ObjectProperty()
    midline_text = StringProperty('')
    midline_markup = BooleanProperty(True)
    midline_font_name = StringProperty('DroidSans')
    midline_font_size = NumericProperty(14)
    midline_color = ListProperty([0, 0, 0, 1])

    footer = ObjectProperty()
    footer_text = StringProperty('')
    footer_markup = BooleanProperty(True)
    footer_font_name = StringProperty('DroidSans')
    footer_font_size = NumericProperty(10)
    footer_color = ListProperty([0, 0, 0, 1])

    text = StringProperty('')
    text_color = ListProperty([0, 0, 0, 1])
    markup = BooleanProperty(True)
    shorten = BooleanProperty(True)
    font_name = StringProperty('DroidSans')
    font_size = NumericProperty(12)

    def on_background_source(self, *args):
        if self.background_source:
            self.background_image = Image(source=self.background_source)

    def on_background_image(self, *args):
        if self.background_image is not None:
            self.background_texture = self.background_image.texture

    def on_foreground_source(self, *args):
        if self.foreground_source:
            self.foreground_image = Image(source=self.foreground_source)

    def on_foreground_image(self, *args):
        if self.foreground_image is not None:
            self.foreground_texture = self.foreground_image.texture

    def on_art_source(self, *args):
        if self.art_source:
            self.art_image = Image(source=self.art_source)

    def on_art_image(self, *args):
        if self.art_image is not None:
            self.art_texture = self.art_image.texture

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return
        if 'card' in touch.ud:
            return
        touch.grab(self)
        self.dragging = True
        touch.ud['card'] = self
        touch.ud['idx'] = self.idx
        touch.ud['deck'] = self.deck
        touch.ud['layout'] = self.parent
        self.collide_x = touch.x - self.x
        self.collide_y = touch.y - self.y

    def on_touch_move(self, touch):
        if not self.dragging:
            touch.ungrab(self)
            return
        Logger.debug('Card: on_touch_move{}'.format(touch.pos))
        self.pos = (
            touch.x - self.collide_x,
            touch.y - self.collide_y
        )

    def on_touch_up(self, touch):
        if not self.dragging:
            return
        touch.ungrab(self)
        self.dragging = False


class Foundation(ColorTextureBox):
    color = ListProperty([])
    deck = NumericProperty(0)

    def upd_pos(self, *args):
        self.pos = self.parent._get_foundation_pos(self.deck)

    def upd_size(self, *args):
        self.size = (
            self.parent.card_size_hint_x * self.parent.width,
            self.parent.card_size_hint_y * self.parent.height
        )


class DeckBuilderLayout(Layout, StencilView):
    direction = OptionProperty(
        'ascending', options=['ascending', 'descending']
    )
    card_size_hint_x = BoundedNumericProperty(1, min=0, max=1)
    card_size_hint_y = BoundedNumericProperty(1, min=0, max=1)
    card_size_hint = ReferenceListProperty(card_size_hint_x, card_size_hint_y)
    starting_pos_hint = DictProperty({'x': 0, 'y': 0})
    card_x_hint_step = NumericProperty(0)
    card_y_hint_step = NumericProperty(-1)
    card_hint_step = ReferenceListProperty(card_x_hint_step, card_y_hint_step)
    deck_x_hint_step = NumericProperty(1)
    deck_y_hint_step = NumericProperty(0)
    deck_hint_step = ReferenceListProperty(deck_x_hint_step, deck_y_hint_step)
    decks = ListProperty([[]])  # list of lists of cards
    _foundations = ListProperty([])
    deck_x_hint_offsets = ListProperty([])
    deck_y_hint_offsets = ListProperty([])
    foundation_color = ListProperty([1, 1, 1, 1])
    insertion_deck = BoundedNumericProperty(None, min=0, allownone=True)
    insertion_card = BoundedNumericProperty(None, min=0, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            card_size_hint=self._trigger_layout,
            starting_pos_hint=self._trigger_layout,
            card_hint_step=self._trigger_layout,
            deck_hint_step=self._trigger_layout,
            decks=self._trigger_layout,
            deck_x_hint_offsets=self._trigger_layout,
            deck_y_hint_offsets=self._trigger_layout,
            insertion_deck=self._trigger_layout,
            insertion_card=self._trigger_layout
        )

    def scroll_deck_x(self, decknum, scroll_x):
        if decknum >= len(self.decks):
            raise IndexError("I have no deck at {}".format(decknum))
        if decknum >= len(self.deck_x_hint_offsets):
            self.deck_x_hint_offsets = list(self.deck_x_hint_offsets) + [0] * (
                decknum - len(self.deck_x_hint_offsets) + 1
            )
        self.deck_x_hint_offsets[decknum] += scroll_x
        self._trigger_layout()

    def scroll_deck_y(self, decknum, scroll_y):
        if decknum >= len(self.decks):
            raise IndexError("I have no deck at {}".format(decknum))
        if decknum >= len(self.deck_y_hint_offsets):
            self.deck_y_hint_offsets = list(self.deck_y_hint_offsets) + [0] * (
                decknum - len(self.deck_y_hint_offsets) + 1
            )
        self.deck_y_hint_offsets[decknum] += scroll_y
        self._trigger_layout()

    def scroll_deck(self, decknum, scroll_x, scroll_y):
        self.scroll_deck_x(decknum, scroll_x)
        self.scroll_deck_y(decknum, scroll_y)

    def _get_foundation_pos(self, i):
        (phx, phy) = get_pos_hint(
            self.starting_pos_hint, *self.card_size_hint
        )
        phx += self.deck_x_hint_step * i + self.deck_x_hint_offsets[i]
        phy += self.deck_y_hint_step * i + self.deck_y_hint_offsets[i]
        x = phx * self.width + self.x
        y = phy * self.height + self.y
        return (x, y)

    def _get_foundation(self, i):
        if i >= len(self._foundations) or self._foundations[i] is None:
            oldfound = list(self._foundations)
            extend = i - len(oldfound) + 1
            if extend > 0:
                oldfound += [None] * extend
            width = self.card_size_hint_x * self.width
            height = self.card_size_hint_y * self.height
            found = Foundation(
                pos=self._get_foundation_pos(i), size=(width, height), deck=i
            )
            self.bind(
                pos=found.upd_pos,
                card_size_hint=found.upd_pos,
                deck_hint_step=found.upd_pos,
                size=found.upd_pos,
                deck_x_hint_offsets=found.upd_pos,
                deck_y_hint_offsets=found.upd_pos
            )
            self.bind(
                size=found.upd_size,
                card_size_hint=found.upd_size
            )
            oldfound[i] = found
            self._foundations = oldfound
        return self._foundations[i]

    def on_decks(self, *args):
        if None in (
                self.canvas,
                self.decks,
                self.deck_x_hint_offsets,
                self.deck_y_hint_offsets
        ):
            Clock.schedule_once(self.on_decks, 0)
            return
        decknum = 0
        for deck in self.decks:
            cardnum = 0
            for card in deck:
                if not isinstance(card, Card):
                    raise TypeError("You must only put Card in decks")
                if card not in self.children:
                    self.add_widget(card)
                if card.deck != decknum:
                    card.deck = decknum
                if card.idx != cardnum:
                    card.idx = cardnum
                cardnum += 1
            decknum += 1
        if len(self.deck_x_hint_offsets) < len(self.decks):
            self.deck_x_hint_offsets = list(self.deck_x_hint_offsets) + [0] * (
                len(self.decks) - len(self.deck_x_hint_offsets)
            )
        if len(self.deck_y_hint_offsets) < len(self.decks):
            self.deck_y_hint_offsets = list(self.deck_y_hint_offsets) + [0] * (
                len(self.decks) - len(self.deck_y_hint_offsets)
            )
        self._trigger_layout()

    def point_before_card(self, card, x, y):
        def ycmp():
            if self.card_y_hint_step == 0:
                return False
            elif self.card_y_hint_step > 0:
                # stacking upward
                return y < card.y
            else:
                # stacking downward
                return y > card.top
        if self.card_x_hint_step > 0:
            # stacking to the right
            if x < card.x:
                return True
            return ycmp()
        elif self.card_x_hint_step == 0:
            return ycmp()
        else:
            # stacking to the left
            if x > card.right:
                return True
            return ycmp()

    def point_after_card(self, card, x, y):
        def ycmp():
            if self.card_y_hint_step == 0:
                return False
            elif self.card_y_hint_step > 0:
                # stacking upward
                return y > card.top
            else:
                # stacking downward
                return y < card.y
        if self.card_x_hint_step > 0:
            # stacking to the right
            if x > card.right:
                return True
            return ycmp()
        elif self.card_x_hint_step == 0:
            return ycmp()
        else:
            # stacking to the left
            if x < card.x:
                return True
            return ycmp()

    def on_touch_move(self, touch):
        if (
                'card' not in touch.ud or
                'layout' not in touch.ud or
                touch.ud['layout'] != self
        ):
            return
        if (
                touch.ud['layout'] == self and
                not hasattr(touch.ud['card'], '_topdecked')
        ):
            self.canvas.after.add(touch.ud['card'].canvas)
            touch.ud['card']._topdecked = True
        any_collision = False
        i = 0
        for deck in self.decks:
            cards = [card for card in deck if not card.dragging]
            maxidx = max(card.idx for card in cards) if cards else 0
            if self.direction == 'descending':
                cards.reverse()
            cards_collided = [
                card for card in cards if card.collide_point(*touch.pos)
            ]
            if cards_collided:
                any_collision = True
                collided = cards_collided.pop()
                for card in cards_collided:
                    if card.idx > collided.idx:
                        collided = card
                if collided.deck == touch.ud['deck']:
                    self.insertion_card = (
                        1 if collided.idx == 0 else
                        maxidx + 1 if collided.idx == maxidx else
                        collided.idx + 1 if collided.idx > touch.ud['idx']
                        else collided.idx
                    )
                else:
                    dropdeck = self.decks[collided.deck]
                    maxidx = max(card.idx for card in dropdeck)
                    self.insertion_card = (
                        1 if collided.idx == 0 else
                        maxidx + 1 if collided.idx == maxidx else
                        collided.idx + 1
                    )
                if self.insertion_deck != collided.deck:
                    self.insertion_deck = collided.deck
                return
            else:
                if self.insertion_deck == i:
                    if self.insertion_card in (0, len(deck)):
                        pass
                    elif self.point_before_card(
                            cards[0], *touch.pos
                    ):
                        self.insertion_card = 0
                    elif self.point_after_card(
                        cards[-1], *touch.pos
                    ):
                        self.insertion_card = cards[-1].idx
            i += 1
            if not any_collision:
                i = 0
                for found in self._foundations:
                    if found is not None and found.collide_point(*touch.pos):
                        self.insertion_deck = i
                        self.insertion_card = 0
                        return
                    i += 1

    def on_touch_up(self, touch):
        if (
                'card' not in touch.ud or
                'layout' not in touch.ud or
                touch.ud['layout'] != self
        ):
            return
        if hasattr(touch.ud['card'], '_topdecked'):
            self.canvas.after.remove(touch.ud['card'].canvas)
            del touch.ud['card']._topdecked
        if None not in (self.insertion_deck, self.insertion_card):
            # need to sync to adapter.data??
            card = touch.ud['card']
            del card.parent.decks[card.deck][card.idx]
            for i in range(0, len(card.parent.decks[card.deck])):
                card.parent.decks[card.deck][i].idx = i
            deck = self.decks[self.insertion_deck]
            if self.insertion_card >= len(deck):
                deck.append(card)
            else:
                deck.insert(self.insertion_card, card)
            card.deck = self.insertion_deck
            card.idx = self.insertion_card
            self.insertion_deck = self.insertion_card = None
        self._trigger_layout()

    def on_insertion_card(self, *args):
        if self.insertion_card is not None:
            self._trigger_layout()

    def do_layout(self, *args):
        if self.size == [1, 1]:
            return
        for i in range(0, len(self.decks)):
            self.layout_deck(i)

    def layout_deck(self, i):
        def get_dragidx(cards):
            j = 0
            for card in cards:
                if card.dragging:
                    return j
                j += 1
        # Put a None in the card list in place of the card you're
        # hovering over, if you're dragging another card. This will
        # result in an empty space where the card will go if you drop
        # it now.
        cards = list(self.decks[i])
        dragidx = get_dragidx(cards)
        if dragidx is not None:
            del cards[dragidx]
        if self.insertion_deck == i and self.insertion_card is not None:
            insdx = self.insertion_card
            if dragidx is not None and insdx > dragidx:
                insdx -= 1
            cards.insert(insdx, None)
        if self.direction == 'descending':
            cards.reverse()
        # Work out the initial pos_hint for this deck
        (phx, phy) = get_pos_hint(self.starting_pos_hint, *self.card_size_hint)
        phx += self.deck_x_hint_step * i + self.deck_x_hint_offsets[i]
        phy += self.deck_y_hint_step * i + self.deck_y_hint_offsets[i]
        (w, h) = self.size
        (x, y) = self.pos
        # start assigning pos and size to cards
        found = self._get_foundation(i)
        if found in self.children:
            self.remove_widget(found)
        self.add_widget(found)
        for card in cards:
            if card is not None:
                if card in self.children:
                    self.remove_widget(card)
                (shw, shh) = self.card_size_hint
                card.pos = (
                    x + phx * w,
                    y + phy * h
                )
                card.size = (w * shw, h * shh)
                self.add_widget(card)
            phx += self.card_x_hint_step
            phy += self.card_y_hint_step


class ScrollBarBar(ColorTextureBox):
    def on_touch_down(self, touch):
        if self.parent is None:
            return
        if self.collide_point(*touch.pos):
            self.parent.bar_touched(self, touch)


class DeckBuilderScrollBar(FloatLayout):
    orientation = OptionProperty(
        'vertical',
        options=['horizontal', 'vertical']
    )
    deckbuilder = ObjectProperty()
    deckidx = NumericProperty(0)
    scrolling = BooleanProperty(False)
    scroll_min = NumericProperty(-1)
    scroll_max = NumericProperty(1)

    scroll_hint = AliasProperty(
        lambda self: self.scroll_max - self.scroll_min,
        lambda self, v: None,
        bind=('scroll_min', 'scroll_max')
    )
    _scroll = NumericProperty(0)

    def _get_scroll(self):
        zero = self._scroll - self.scroll_min
        return zero / self.scroll_hint

    def _set_scroll(self, v):
        if v < 0:
            v = 0
        if v > 1:
            v = 1
        normal = v * self.scroll_hint
        self._scroll = self.scroll_min + normal

    scroll = AliasProperty(
        _get_scroll,
        _set_scroll,
        bind=('_scroll', 'scroll_min', 'scroll_max')
    )

    def _get_vbar(self):
        if self.deckbuilder is None:
            return (0, 1)
        vh = self.deckbuilder.height * self.scroll_hint
        h = self.height
        if vh < h or vh == 0:
            return (0, 1)
        ph = max(0.01, h / vh)
        sy = min(1.0, max(0.0, self.scroll))
        py = (1 - ph) * sy
        return (py, ph)
    vbar = AliasProperty(
        _get_vbar,
        None,
        bind=('_scroll', 'scroll_min', 'scroll_max')
    )

    def _get_hbar(self):
        if self.deckbuilder is None:
            return (0, 1)
        vw = self.deckbuilder.width * self.scroll_hint
        w = self.width
        if vw < w or vw == 0:
            return (0, 1)
        pw = max(0.01, w / vw)
        sx = min(1.0, max(0.0, self.scroll))
        px = (1 - pw) * sx
        return (px, pw)

    hbar = AliasProperty(
        _get_hbar,
        None,
        bind=('_scroll', 'scroll_min', 'scroll_max')
    )
    bar_color = ListProperty([.7, .7, .7, .9])
    bar_inactive_color = ListProperty([.7, .7, .7, .2])
    bar_texture = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            _scroll=self._trigger_layout,
            scroll_min=self._trigger_layout,
            scroll_max=self._trigger_layout
        )

    def do_layout(self, *args):
        if 'bar' not in self.ids:
            Clock.schedule_once(self.do_layout)
            return
        if self.orientation == 'horizontal':
            self.ids.bar.size_hint_x = self.hbar[1]
            self.ids.bar.pos_hint = {'x': self.hbar[0], 'y': 0}
        else:
            self.ids.bar.size_hint_y = self.vbar[1]
            self.ids.bar.pos_hint = {'x': 0, 'y': self.vbar[0]}
        super().do_layout(*args)

    def upd_scroll(self, *args):
        att = 'deck_{}_hint_offsets'.format(
            'x' if self.orientation == 'horizontal' else 'y'
        )
        self._scroll = getattr(self.deckbuilder, att)[self.deckidx]

    def on_deckbuilder(self, *args):
        if self.deckbuilder is None:
            return
        att = 'deck_{}_hint_offsets'.format(
            'x' if self.orientation == 'horizontal' else 'y'
        )
        offs = getattr(self.deckbuilder, att)
        if len(offs) <= self.deckidx:
            Clock.schedule_once(self.on_deckbuilder, 0)
            return
        self.bind(scroll=self.handle_scroll)
        self.deckbuilder.bind(**{att: self.upd_scroll})
        self.upd_scroll()
        self.deckbuilder._trigger_layout()

    def handle_scroll(self, *args):
        if 'bar' not in self.ids:
            Clock.schedule_once(self.handle_scroll, 0)
            return
        att = 'deck_{}_hint_offsets'.format(
            'x' if self.orientation == 'horizontal' else 'y'
        )
        offs = list(getattr(self.deckbuilder, att))
        if len(offs) <= self.deckidx:
            Clock.schedule_once(self.on_scroll, 0)
            return
        offs[self.deckidx] = self._scroll
        setattr(self.deckbuilder, att, offs)
        self.deckbuilder._trigger_layout()

    def bar_touched(self, bar, touch):
        self.scrolling = True
        self._start_bar_pos_hint = get_pos_hint(bar.pos_hint, *bar.size_hint)
        self._start_touch_pos_hint = (
            touch.x / self.width,
            touch.y / self.height
        )
        self._start_bar_touch_hint = (
            self._start_touch_pos_hint[0] - self._start_bar_pos_hint[0],
            self._start_touch_pos_hint[1] - self._start_bar_pos_hint[1]
        )
        touch.grab(self)

    def on_touch_move(self, touch):
        if not self.scrolling or 'bar' not in self.ids:
            touch.ungrab(self)
            return
        touch.push()
        touch.apply_transform_2d(self.parent.to_local)
        touch.apply_transform_2d(self.to_local)
        if self.orientation == 'horizontal':
            hint_right_of_bar = (touch.x - self.ids.bar.x) / self.width
            hint_correction = hint_right_of_bar - self._start_bar_touch_hint[0]
            self.scroll += hint_correction
        else:  # self.orientation == 'vertical'
            hint_above_bar = (touch.y - self.ids.bar.y) / self.height
            hint_correction = hint_above_bar - self._start_bar_touch_hint[1]
            self.scroll += hint_correction
        touch.pop()

    def on_touch_up(self, touch):
        self.scrolling = False

kv = """
<ColorTextureBox>:
    canvas:
        Color:
            rgba: root.color
        Rectangle:
            texture: root.texture
            pos: root.pos
            size: root.size
        Color:
            rgba: root.outline_color
        Line:
            points: [self.x, self.y, self.right, self.y, self.right, self.top, self.x, self.top, self.x, self.y]
        Color:
            rgba: [1, 1, 1, 1]
<Foundation>:
    color: [0, 0, 0, 0]
    outline_color: [1, 1, 1, 1]
<Card>:
    headline: headline
    midline: midline
    footer: footer
    art: art
    foreground: foreground
    canvas:
        Color:
            rgba: root.background_color
        Rectangle:
            texture: root.background_texture
            pos: root.pos
            size: root.size
        Color:
            rgba: root.outline_color
        Line:
            points: [self.x, self.y, self.right, self.y, self.right, self.top, self.x, self.top, self.x, self.y]
        Color:
            rgba: [1, 1, 1, 1]
    BoxLayout:
        size_hint: 0.9, 0.9
        pos_hint: {'x': 0.05, 'y': 0.05}
        orientation: 'vertical'
        canvas:
            Color:
                rgba: root.content_outline_color
            Line:
                points: [self.x, self.y, self.right, self.y, self.right, self.top, self.x, self.top, self.x, self.y]
            Color:
                rgba: [1, 1, 1, 1]
        Label:
            id: headline
            text: root.headline_text
            markup: root.headline_markup
            font_name: root.headline_font_name
            font_size: root.headline_font_size
            color: root.headline_color
            size_hint: (None, None)
            size: self.texture_size
        ColorTextureBox:
            id: art
            color: root.art_color
            texture: root.art_texture
            outline_color: root.art_outline_color if root.show_art else [0, 0, 0, 0]
            size_hint: (1, 1) if root.show_art else (None, None)
            size: (0, 0)
        Label:
            id: midline
            text: root.midline_text
            markup: root.midline_markup
            font_name: root.midline_font_name
            font_size: root.midline_font_size
            color: root.midline_color
            size_hint: (None, None)
            size: self.texture_size
        ColorTextureBox:
            id: foreground
            color: root.foreground_color
            outline_color: root.foreground_outline_color
            texture: root.foreground_texture
            Label:
                text: root.text
                color: root.text_color
                markup: root.markup
                font_name: root.font_name
                font_size: root.font_size
                text_size: foreground.size
                size_hint: (None, None)
                size: self.texture_size
                pos: foreground.pos
                valign: 'top'
        Label:
            id: footer
            text: root.footer_text
            markup: root.footer_markup
            font_name: root.footer_font_name
            font_size: root.footer_font_size
            color: root.footer_color
            size_hint: (None, None)
            size: self.texture_size
<DeckBuilderScrollBar>:
    ScrollBarBar:
        id: bar
        color: root.bar_color if root.scrolling else root.bar_inactive_color
        texture: root.bar_texture
"""
Builder.load_string(kv)


if __name__ == '__main__':
    deck0 = [
        Card(
            background_color=[0, 1, 0, 1],
            headline_text='Card {}'.format(i),
            art_color=[1, 0, 0, 1],
            midline_text='0deck',
            foreground_color=[0, 0, 1, 1],
            text='The quick brown fox jumps over the lazy dog',
            text_color=[1, 1, 1, 1],
            footer_text=str(i)
        )
        for i in range(0, 9)
    ]
    deck1 = [
        Card(
            background_color=[0, 0, 1, 1],
            headline_text='Card {}'.format(i),
            art_color=[0, 1, 0, 1],
            show_art=False,
            midline_text='1deck',
            foreground_color=[1, 0, 0, 1],
            text='Have a steak at the porter house bar',
            text_color=[1, 1, 0, 1],
            footer_text=str(i)
        )
        for i in range(0, 9)
    ]
    from kivy.base import runTouchApp
    from kivy.core.window import Window
    from kivy.modules import inspector
    builder = DeckBuilderLayout(
        card_size_hint=(0.15, 0.3),
        pos_hint={'x': 0, 'y': 0},
        starting_pos_hint={'x': 0.1, 'top': 0.9},
        card_hint_step=(0.05, -0.1),
        deck_hint_step=(0.4, 0),
        decks=[deck0, deck1],
        deck_y_hint_offsets=[0, 1]
    )
    layout = BoxLayout(orientation='horizontal')
    left_bar = DeckBuilderScrollBar(
        deckbuilder=builder,
        orientation='vertical',
        size_hint_x=0.1,
        deckidx=0
    )
    right_bar = DeckBuilderScrollBar(
        deckbuilder=builder,
        orientation='vertical',
        size_hint_x=0.1,
        deckidx=1
    )
    layout.add_widget(left_bar)
    layout.add_widget(builder)
    layout.add_widget(right_bar)
    inspector.create_inspector(Window, layout)
    runTouchApp(layout)
