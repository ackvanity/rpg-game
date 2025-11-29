import asyncio
import urwid
import logging
from typing import Literal

class SimpleTextRenderer:
    def __init__(self):
        self.print_fn = print
        self.input_fn = input

    def send_dialogue(self, character: str, line: str):
        self.print_fn(f"{character.upper()}: {line}")

    def send_story(self, text: str):
        self.print_fn(f"{text}")

    def send_option(self, options: list[str]) -> int:
        for i, choice in enumerate(options):
            self.print_fn(f"{i + 1}. {choice}")
        return int(self.input_fn("Choose an choice: ")) - 1

class UrwidTextRenderer:
    async def placeholder(self):
        pass

    def __init__(self, exit_game):
        self.exit_game = exit_game
        self.logger = logging.getLogger("GameLogger")
        self.callback_asyncio = lambda: self.placeholder()

        self.palette = [
            ("character_speak", "default,bold", "default", "bold"),
            ("danger_warning", "default,bold", "default", "bold")
        ]

        self.widgets: list[urwid.Widget] = [urwid.Text("HTTYD")]
        self.pile = urwid.Pile(widget_list=self.widgets)
        self.scrollable = urwid.Scrollable(self.pile) # type: ignore
        self.scrollbar = urwid.ScrollBar(self.scrollable) # type: ignore

        asyncio_loop = asyncio.get_event_loop()
        urwid_loop = urwid.AsyncioEventLoop(loop=asyncio_loop)

        self.main_loop = urwid.MainLoop(self.scrollbar, self.palette, event_loop=urwid_loop, unhandled_input=lambda x: self.handle_input(x))

    def start(self):
        self.logger.info("urwid main loop starting.")
        asyncio.get_event_loop().create_task(self.render_tick())
        asyncio.get_event_loop().create_task(self.callback_asyncio())
        self.main_loop.run()
    
    async def render_tick(self):
        while True:
            self.pile.widget_list = self.widgets
            self.main_loop.draw_screen()
            await asyncio.sleep(0)

    def handle_input(self, key):
        if key in ('q', 'Q'):
            asyncio.get_event_loop().create_task(self.exit_game())
            self.widgets = [urwid.Text(("danger_warning", "SAVING GAME STATE..."))]

    async def send_dialogue(self, character: str, line: str):
        self.widgets.append(urwid.Text([("character_speak", character.upper()), ": ", line]))

    async def send_story(self, text: str):
        self.widgets.append(urwid.Text([text]))

    async def send_option(self, options: list[str]) -> int:
        selected_index = -1
        done_event = asyncio.Event()

        def on_selection(index):
            nonlocal selected_index
            selected_index = index
            done_event.set()

        buttons = [urwid.Button(option, lambda btn, i=idx: on_selection(i)) for idx, option in enumerate(options)]
        self.widgets.append(urwid.Pile(buttons))

        await done_event.wait()

        self.widgets.pop()

        return selected_index

renderer: UrwidTextRenderer = None # type: ignore