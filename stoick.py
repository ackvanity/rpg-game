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
            ("bg1", "white", "black", None, "white", "#7A6656"),
            ("bg2", "white", "black", None, "white", "#BD8456")
        ]

        self.listwalker = urwid.SimpleListWalker([urwid.Text("HTTYD")])
        self.listbox = urwid.AttrMap(sven.BoundedContainer(urwid.AttrMap(urwid.ListBox(self.listwalker), "bg1"), max_width=100, align="center"), "bg2")

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


renderer: UrwidTextRenderer = None  # type: ignore
