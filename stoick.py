from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, VerticalGroup, Center, Middle
from textual.widgets import Static, Button, Input
from textual.widget import Widget
from textual.message import Message
import pyfiglet
import asyncio
from typing import Any

class ScreenRider(Widget):
    class ExitGame(Message):
        pass

    async def mission(self, renderer) -> Any: ...

class BigText(Static):
    def __init__(self, text: str, font: str = "standard", *args, **kwargs):
        ascii_art = pyfiglet.figlet_format(text, font=font, width=120)
        super().__init__(ascii_art, markup=False, *args, **kwargs)

class TextualRenderer(App):
    CSS_PATH = [
        "css/ack/game_intro.tcss",
        "css/ack/viking_select_card.tcss",
        "css/astrid/astrid.tcss",
        "css/base.tcss",
    ]

    bid_scout = {}

    def __init__(self, exit_game, riders):
        super().__init__()
        self.exit_game = exit_game
        self.app_container: VerticalScroll = None  # type: ignore

        # For button-based choice screens
        self.choice_event = asyncio.Event()
        self.choice_result = None  # type: ignore
        self.riders = riders

    def on_ready(self):
        # This runs after the UI is ready.
        asyncio.create_task(self.riders())

    def compose(self) -> ComposeResult:
        self.app_container = VerticalScroll(id="dialogue")
        yield self.app_container

    async def on_screen_rider_exit_game(self):
        await self.exit_game()
        exit()

    async def on_button_pressed(self, event: Button.Pressed):
        async_event = self.choice_event
        bid = event.button.id

        async def set_event():
            nonlocal async_event
            await asyncio.sleep(0)
            async_event.set()

        if bid and bid.startswith("opt_"):
            self.choice_result = int(bid.split("_")[1])
            asyncio.create_task(set_event())
        elif bid in self.bid_scout:
            await self.bid_scout[bid]()


    # ---------- Viking creation ----------
    async def send_viking_create(self):
        self.app_container.remove_children()
        done = asyncio.Event()
        result = (False, "", "")

        def finish(res):
            nonlocal result
            result = res
            done.set()

        self.app_container.mount(Static("[bold]CREATE VIKING[/bold]"))

        fullname = Input(placeholder="Full name")
        name = Input(placeholder="Nickname")
        self.app_container.mount(fullname)
        self.app_container.mount(name)

        # event handlers: using closures because Textual's handler signature is flexible
        async def on_back():
            finish((False, "", ""))

        async def on_create():
            finish((True, name.value, fullname.value))

        self.bid_scout["on_back"] = on_back
        self.bid_scout["on_create"] = on_create

        # Buttons
        back_btn = Button("Back", id="on_back")
        create_btn = Button("Create Viking", id="on_create")

        self.app_container.mount(back_btn)
        self.app_container.mount(create_btn)

        await done.wait()

        del self.bid_scout["on_back"]
        del self.bid_scout["on_create"]

        return result

    async def send_rider(self, rider: ScreenRider):
        return await rider.mission(self)

    async def clear_screen(self, ask=True):
        if ask:
            continue_event = asyncio.Event()

            async def continue_path():
                continue_event.set()

            next_btn = Button("Continue", id="continue")
            self.bid_scout["continue"] = continue_path
            self.app_container.mount(next_btn)
            await continue_event.wait()

        to_remove = []
        for child in self.app_container.children:
            to_remove.append(child)

        for child in to_remove:
            await child.remove()


renderer: TextualRenderer = None  # type: ignore
