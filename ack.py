from typing import NoReturn, Any
from textual.widgets import Button, Static
from textual.containers import VerticalGroup, Middle, Center, Horizontal
from textual.app import ComposeResult
import uuid
import asyncio
import astrid
import gobber
import stoick


class GameIntro(stoick.ScreenRider):

    start_event = asyncio.Event()

    async def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id

        if bid == "start":
            self.start_event.set()
            event.stop()

        if bid == "exit":
            self.post_message(self.ExitGame())

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                yield Static("HOW TO TRAIN YOUR", id="pre_title_banner")

            with Center():
                yield stoick.BigText(
                    "DRAGON", "diet_cola", id="title_banner"
                )  # diet_cola, roman(?),

            with Center():
                yield Button("Start", id="start")
                yield Button("Exit", id="exit")
    
    async def mission(self, renderer):
        self.start_event.clear()
        
        await renderer.clear_screen(ask=False)

        renderer.app_container.mount(self)

        await self.start_event.wait()
        await self.remove()

class VikingSelectCard(VerticalGroup):
    def __init__(self, shortname, fullname, idx, *args, **kwargs):
        self.shortname = shortname
        self.fullname = fullname
        self.idx = idx
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with VerticalGroup():
                yield Static(self.shortname, classes="viking_name")
                yield Static(self.fullname, classes="viking_fullname")
            yield Button("Select", id=f"opt_{self.idx}")


class VikingSelect(stoick.ScreenRider):
    vikings: list[tuple[str, str, Any]] = []
    select_event: asyncio.Event = asyncio.Event()
    selected_viking: int = -1

    def __init__(self, vikings: list[tuple[str, str, Any]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vikings = vikings

    async def on_button_pressed(self, event: Button.Pressed):
        bid: str = event.button.id  # type: ignore

        if bid.startswith("opt_"):
            self.selected_viking = int(bid.split("_")[1])
            self.select_event.set()
            event.stop()
        elif bid == "back":
            self.selected_viking = -1
            self.select_event.set()
            event.stop()
        elif bid == "new_viking":
            self.selected_viking = len(self.vikings)
            self.select_event.set()
            event.stop()
        

    def compose(self) -> ComposeResult:
        with Middle():

            with Center():
                yield stoick.BigText("SELECT VIKING", "diet_cola", id="banner")

            with Center():
                yield Button("Back", id="back")

            for idx, (short, full, _) in enumerate(self.vikings):
                with Center():
                    card = VikingSelectCard(short, full, idx)
                    yield card

            yield Button("New Viking", id=f"new_viking")

    async def mission(self, renderer: stoick.TextualRenderer):
        self.select_event.clear()
        renderer.app_container.mount(self)

        await self.select_event.wait()

        await self.remove()
        return self.selected_viking


async def handles_this(current_entity: gobber.EntityID):
    if current_entity[0] == "init":
        return True

    return False


async def draw_this(current_entity: gobber.EntityID):
    if current_entity[0] == "init" and current_entity[1] == "start_screen":
        await stoick.renderer.clear_screen(ask=False)
        await stoick.renderer.send_rider(GameIntro())
        gobber.entity_stack.append(gobber.EntityID(("init", "viking_select")))
        await render_state()
    elif current_entity[0] == "init" and current_entity[1] == "viking_select":
        await stoick.renderer.clear_screen(ask=False)
        vikings_list = gobber.list_vikings()
        viking_idx = await stoick.renderer.send_rider(VikingSelect(vikings_list))

        if viking_idx == -1:
            gobber.entity_stack.pop()
            await render_state()
        elif viking_idx == len(vikings_list):
            gobber.entity_stack.append(gobber.EntityID(("init", "viking_create")))
            await render_state()
        else:
            gobber.set_player_file(vikings_list[viking_idx][2])
            gobber.load_game_state()
            gobber.preload_story_entities()
            await asyncio.sleep(0)
            await stoick.renderer.clear_screen(ask=False)
            await render_state()
    elif current_entity[0] == "init" and current_entity[1] == "viking_create":
        go_ahead, viking_name, viking_fullname = (
            await stoick.renderer.send_viking_create()
        )

        if not go_ahead:
            gobber.entity_stack.pop()
            await render_state()

        if go_ahead:
            filename = str(uuid.uuid4()) + ".json"
            gobber.set_player_file(filename)
            gobber.set_player_state(
                {
                    "name": viking_name,
                    "fullname": viking_fullname,
                    "states": gobber.get_player_data()["states"],
                }
            )
            gobber.preload_story_entities()

            await stoick.renderer.clear_screen(ask=False)

            astrid.reveal_location(gobber.EntityID(("location", "berk_square")))
            gobber.save_game_state()
            await render_state()


async def render_state() -> NoReturn:
    raise Exception("ERROR: Render_state not defiend")
