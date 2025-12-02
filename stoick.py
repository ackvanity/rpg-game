from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static, Button, Input
import asyncio


class TextualRenderer(App):

    # CSS_PATH = "style.css"   # optional

    bid_scout = {}

    def __init__(self, exit_game, riders):
        super().__init__()
        self.exit_game = exit_game
        self.dialogue_container: VerticalScroll = None  # type: ignore

        # For button-based choice screens
        self.choice_event = asyncio.Event()
        self.choice_result = None  # type: ignore
        self.riders = riders

    def on_ready(self):
        # This runs after the UI is ready.
        asyncio.create_task(self.riders())

    def compose(self) -> ComposeResult:
        self.dialogue_container = VerticalScroll(id="dialogue")
        yield self.dialogue_container

    # ---------- Utility to add text ----------
    def add_text(self, text, style="default"):
        self.dialogue_container.mount(Static(text, classes=style))

    # ---------- Sending dialogue/story ----------
    async def send_dialogue(self, character: str, line: str):
        self.add_text(f"[cyan bold]{character.upper()}[/cyan bold]: {line}")

    async def send_story(self, text: str):
        self.add_text(text)

    # ---------- Simple option selection ----------
    async def send_option(self, options: list[str]) -> int:
        self.choice_event.clear()
        self.choice_result: int = None  # type: ignore

        buttons = []
        for idx, option in enumerate(options):
            b = Button(option, id=f"opt_{idx}")
            buttons.append(b)
            self.dialogue_container.mount(b)

        # Wait until a button handler sets choice_result
        await self.choice_event.wait()

        for btn in buttons:
            await btn.remove()

        return self.choice_result

    # ---------- Button click handler ----------
    async def on_button_pressed(self, event: Button.Pressed):
        async_event = self.choice_event
        async def set_event():
            nonlocal async_event
            await asyncio.sleep(0)
            async_event.set()

        bid = event.button.id
        if bid and bid.startswith("opt_"):
            self.choice_result = int(bid.split("_")[1])
            async_event = self.choice_event
            asyncio.create_task(set_event())
        elif bid == "start":
            async_event = self.start_event
            asyncio.create_task(set_event())
        elif bid == "exit":
            await self.exit_game()
            self.exit()
        elif bid in self.bid_scout:
            await self.bid_scout[bid]()

    # ---------- Game start screen ----------
    async def send_game_start(self):
        self.start_event = asyncio.Event()
        self.dialogue_container.mount(
            Static("[bold red]DRAGONS[/bold red]", id="banner")
        )
        self.dialogue_container.mount(Button("Start", id="start"))
        self.dialogue_container.mount(Button("Exit", id="exit"))
        await self.start_event.wait()

    # ---------- Viking selection ----------
    async def send_viking_select(self, viking_list):
        self.choice_event.clear()
        self.choice_result = None  # type: ignore

        self.dialogue_container.remove_children()
        self.dialogue_container.mount(Static("[bold]SELECT VIKING[/bold]"))

        # Back button
        back_btn = Button("Back", id="opt_-1")
        self.dialogue_container.mount(back_btn)

        for idx, (short, full, _) in enumerate(viking_list):
            self.dialogue_container.mount(Static(short))
            self.dialogue_container.mount(Static(full))
            self.dialogue_container.mount(Button("Select", id=f"opt_{idx}"))

        new_btn = Button("New Viking", id=f"opt_{len(viking_list)}")
        self.dialogue_container.mount(new_btn)

        await self.choice_event.wait()
        return self.choice_result

    # ---------- Viking creation ----------
    async def send_viking_create(self):
        self.dialogue_container.remove_children()
        done = asyncio.Event()
        result = (False, "", "")

        def finish(res):
            nonlocal result
            result = res
            done.set()

        self.dialogue_container.mount(Static("[bold]CREATE VIKING[/bold]"))

        fullname = Input(placeholder="Full name")
        name = Input(placeholder="Nickname")
        self.dialogue_container.mount(fullname)
        self.dialogue_container.mount(name)

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

        self.dialogue_container.mount(back_btn)
        self.dialogue_container.mount(create_btn)

        await done.wait()

        del self.bid_scout["on_back"]
        del self.bid_scout["on_create"]

        return result

    async def clear_screen(self, ask=True):


        if ask:
            continue_event = asyncio.Event()
            async def continue_path():
                continue_event.set()
            
            next_btn = Button("Continue", id="continue")
            self.bid_scout["continue"] = continue_path
            self.dialogue_container.mount(next_btn)
            await continue_event.wait()

        to_remove = []
        for child in self.dialogue_container.children:
            to_remove.append(child)

        for child in to_remove:
            await child.remove()
        

renderer: TextualRenderer = None  # type: ignore
