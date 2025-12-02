import asyncio
import urwid
import ruffnut
import sven


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
    # _widgets: list[urwid.Widget]

    # @property
    # def widgets(self):
    #     return self._widgets

    # @widgets.setter
    # def widgets(self, value):
    #     self._widgets = value
    #     asyncio.get_event_loop().create_task(self.render_tick())

    async def placeholder(self):
        pass

    def __init__(self, exit_game):
        self.exit_game = exit_game
        self.logger = ruffnut.logger
        self.callback_asyncio = lambda: self.placeholder()

        self.palette = [
            ("character_speak", "light cyan,bold", "default"),
            ("danger_warning", "default,bold", "default", "bold"),
            ("banner", "dark red", "black", "default", "#B31D2C", "#527b95"),
            ("bg1", "white", "black", None, "white", "#517787"),
            ("bg2", "white", "black", None, "white", "#BD8456"),
        ]

        self.listwalker = urwid.SimpleListWalker([urwid.Text("HTTYD")])
        self.listbox = urwid.AttrMap(
            sven.BoundedContainer(
                urwid.AttrMap(urwid.ListBox(self.listwalker), "bg1"),
                max_width=100,
                align="center",
            ),
            "bg2",
        )

        asyncio_loop = asyncio.get_event_loop()
        urwid_loop = urwid.AsyncioEventLoop(loop=asyncio_loop)

        self.main_loop = urwid.MainLoop(
            self.listbox,
            self.palette,
            event_loop=urwid_loop,
            unhandled_input=lambda x: self.handle_input(x),
        )

    def start(self):
        self.logger.info("urwid main loop starting.")
        self.main_loop.screen.set_terminal_properties(colors=256)
        asyncio.get_event_loop().create_task(self.render_tick())
        asyncio.get_event_loop().create_task(self.callback_asyncio())
        self.main_loop.run()

    async def render_tick(self):
        while True:
            self.main_loop.draw_screen()
            await asyncio.sleep(0)

    def handle_input(self, key):
        if key in ("q", "Q"):
            asyncio.get_event_loop().create_task(self.exit_game())
            self.listwalker[:] = [
                urwid.Text(("danger_warning", "SAVING GAME STATE..."))
            ]

    async def send_dialogue(self, character: str, line: str):
        self.listwalker.append(
            urwid.Text([("character_speak", character.upper()), ": ", line])
        )

    async def send_story(self, text: str):
        self.listwalker.append(urwid.Text([text]))

    async def send_option(self, options: list[str]) -> int:
        selected_index = -1
        done_event = asyncio.Event()

        def on_selection(index):
            nonlocal selected_index
            selected_index = index
            done_event.set()

        buttons = [
            urwid.Button(option, lambda btn, i=idx: on_selection(i))
            for idx, option in enumerate(options)
        ]
        self.listwalker.append(urwid.Pile(buttons))

        await done_event.wait()

        self.listwalker.pop()

        return selected_index

    async def send_game_start(self):
        start_event = asyncio.Event()

        def on_start(btn):
            start_event.set()

        def on_exit(btn):
            asyncio.get_event_loop().create_task(self.exit_game())

        self.listwalker[:] = [
            urwid.Padding(
                urwid.BigText(("banner", "DRAGONS"), urwid.HalfBlock5x4Font()),
                align="center",
                width="clip",
            ),
            urwid.Padding(urwid.Text("On CLI"), align="center", width="clip"),
            urwid.Button("Start", on_start),
            urwid.Button("Exit", on_exit),
        ]

        self.main_loop.draw_screen()

        await start_event.wait()

    async def send_viking_select(self, viking_list):
        self.main_loop.draw_screen()
        selected_index = -1
        done_event = asyncio.Event()

        def on_selection(index):
            nonlocal selected_index
            selected_index = index
            done_event.set()

        self.listwalker[:] = [
            urwid.Padding(
                urwid.BigText(("banner", "SELECT VIKING"), urwid.Thin3x3Font()),
                align="center",
                width="clip",
            ),
            urwid.Button("Back", lambda btn: on_selection(-1)),
        ]

        for i, viking in enumerate(viking_list):
            self.listwalker.append(
                urwid.Pile(
                    [
                        urwid.Text(("viking_name", viking[0])),
                        urwid.Text(("viking_fullname", viking[1])),
                        urwid.Button("Select", lambda btn: on_selection(i)),
                    ]
                ),
            )

        self.listwalker.append(
            urwid.Button("New Viking", lambda btn: on_selection(len(viking_list))),
        )

        await done_event.wait()
        self.listwalker[:] = [urwid.Text("Loading")]
        return selected_index

    async def send_viking_create(self):
        result = (False, "", "")
        done_event = asyncio.Event()

        def on_result(res):
            nonlocal result
            result = res
            done_event.set()

        self.listwalker[:] = [
            urwid.Padding(
                urwid.BigText(("banner", "CREATE VIKING"), urwid.HalfBlock5x4Font()),
                align="center",
                width="clip",
            ),
            urwid.Button("Back", lambda btn: on_result((False, "", ""))),
            fullname_edit := urwid.Edit("What's going to be your full name? "),
            name_edit := urwid.Edit("Who should others call you? "),
            urwid.Button(
                "Create Viking",
                lambda btn: on_result(
                    (True, name_edit.edit_text, fullname_edit.edit_text)
                ),
            ),
        ]

        self.main_loop.draw_screen()

        await done_event.wait()
        self.listwalker[:] = [urwid.Text("Loading")]
        return result


from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static, Button, Input
from textual.reactive import reactive
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
        self.log("PRE_OPTIONS", self.dialogue_container.children)
        self.choice_event.clear()
        self.choice_result: int = None  # type: ignore

        print("WAITING")
        buttons = []
        try:
            for idx, option in enumerate(options):
                b = Button(option, id=f"opt_{idx}")
                buttons.append(b)
                self.dialogue_container.mount(b)
        except Exception as e:
            print(e)

        print("WAITING")
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
            print(short, full)
            self.dialogue_container.mount(Static(short))
            self.dialogue_container.mount(Static(full))
            self.dialogue_container.mount(Button("Select", id=f"opt_{idx}"))

        print("CHECK")
        new_btn = Button("New Viking", id=f"opt_{len(viking_list)}")
        self.dialogue_container.mount(new_btn)

        print("FULL RENDER")

        await self.choice_event.wait()
        print("ENTERING", self.choice_result)
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

        print("RENDER")
        await done.wait()

        del self.bid_scout["on_back"]
        del self.bid_scout["on_create"]

        return result

    async def clear_screen(self, ask=True):

        if ask:
            continue_event = asyncio.Event()
            next_btn = Button("Continue", id="continue")
            self.bid_scout["continue"] = lambda: continue_event.set()
            self.dialogue_container.mount(next_btn)
            await continue_event.wait()

        to_remove = []
        for child in self.dialogue_container.children:
            to_remove.append(child)

        for child in to_remove:
            try:
                self.log("REMOVING", child)
                await child.remove()
            except Exception as e:
                self.log(e)
        
        self.log("CLEANUP", self.dialogue_container.children)

renderer: TextualRenderer = None  # type: ignore
