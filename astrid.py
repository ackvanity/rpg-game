import random
from typing import NoReturn, Any
import random
import asyncio

from ruffnut import logger
from tuffnut import exit_game
import gobber
import stoick
from textual.widgets import Static, Button
from textual.widget import Widget
from textual.app import ComposeResult
from textual.containers import VerticalGroup, Horizontal, CenterMiddle

class AstridWidget(Widget):
    async def mission(self, rider: Any) -> Any: ...


class Astrid(VerticalGroup, stoick.ScreenRider):

    def __init__(self, *children: AstridWidget, **kwargs):
        super().__init__(*children, **kwargs)
        self.to_mount: list[Widget] = []
        self.mounted = False
        self.center = CenterMiddle()
    
    async def leave(self):
        if self.mounted:
            to_remove = list(self.children)

            for child in to_remove:
                self.to_mount.append(child)
                await child.remove()

            await self.remove()
            await self.center.remove()

            self.mounted = False
    
    async def assign(self, renderer: stoick.TextualRenderer):
        if not self.mounted:
            renderer.app_container.mount(self.center)
            self.center.mount(self)

            self.mounted = True

        for child in self.to_mount:
            self.mount(child)

    async def mission(self, renderer: stoick.TextualRenderer):
        await self.assign(renderer)

        for candidate in self.to_mount:
            self.mount(candidate)
        
        self.to_mount.clear()

        return await self.children[-1].mission(self)  # type: ignore



class Story(VerticalGroup, AstridWidget):
    def __init__(self, story, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.story = story

    def compose(self) -> ComposeResult:
        yield Static(self.story)

    async def mission(self, rider: Any):
        pass

class Dialogue(AstridWidget):
    def __init__(self, speaker: str, text: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speaker = speaker.upper()
        self.text = text

    def compose(self) -> ComposeResult:
        yield Static(self.speaker, classes="speaker")
        yield Static(self.text, classes="text")

    async def mission(self, rider: Any):
        pass


class Option(VerticalGroup, AstridWidget):
    async def on_button_pressed(self, event: Button.Pressed):
        bid: str = event.button.id  # type: ignore

        if bid.startswith("opt_"):
            self.selected_event.set()
            self.selected_option = int(bid.split("_")[1])
            event.stop()

    def __init__(self, options: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = options
        self.selected_event = asyncio.Event()
        self.selected_option = -1

    def compose(self) -> ComposeResult:
        for idx, option in enumerate(self.options):
            yield Button(option, id=f"opt_{idx}")

    async def mission(self, rider: Any):
        self.selected_event.clear()
        self.selected_option = 0

        await self.selected_event.wait()
        await self.remove()

        return self.selected_option


stormfly = Astrid()


async def _send_story(story: str):
    stormfly.to_mount.append(Story(story))
    return await stoick.renderer.send_rider(stormfly)


async def _send_dialogue(speaker: str, text: str):
    stormfly.to_mount.append(Dialogue(speaker, text))
    return await stoick.renderer.send_rider(stormfly)


async def _send_option(options: list[str]):
    stormfly.to_mount.append(Option(options))
    return await stoick.renderer.send_rider(stormfly)


def _character_talk_to_player(character_entity: gobber.EntityID):
    char_data = gobber.get_entity_data(character_entity)

    def transition_state(option):
        # don't mutate original option objects in char files
        opt = option.copy()
        opt["effect"] = (
            f"gobber.entity_states[gobber.entity_stack[-1]].state = '{opt['state']}'; gobber.entity_stack[-1].step = 0"
        )
        return opt

    options = list(map(transition_state, char_data.get("option_menus", [])))

    # Append quests that can start
    for i, quest in enumerate(gobber.quest_triggers.get(str(character_entity), [])):
        quest_data = gobber.get_entity_data(quest)
        # check start_condition and quest status
        if (
            gobber.run_effect(quest_data["start_condition"], quest)
            and gobber.entity_states[quest].variables.get("status") == "idle"
        ):
            options.append(
                {
                    "text": quest_data["start_line"],
                    "effect": (
                        f"gobber.entity_states[gobber.quest_triggers['{str(character_entity)}'][{i}]].variables['status']='inprogress'; "
                        f"gobber.entity_states[gobber.quest_triggers['{str(character_entity)}'][{i}]].state='{quest_data['start_state']}'; "
                        f"gobber.entity_states[gobber.quest_triggers['{str(character_entity)}'][{i}]].step = 0; "
                        f"gobber.entity_stack.append(gobber.quest_triggers['{str(character_entity)}'][{i}])"
                    ),
                }
            )

    # Add farewell option
    player_farewell = random.choice(
        gobber.get_player_data()["dialogues"]["characters"]["farewell"]
    )
    options.append(
        {
            "text": player_farewell.format(character_name=char_data["name"]),
            "effect": "gobber.entity_stack.pop()",
        }
    )

    return options


def _location_world_to_player(location_entity: gobber.EntityID):
    assert location_entity[0] == "location"

    options = []

    # Append quests that can start
    for i, quest in enumerate(gobber.quest_triggers.get(str(location_entity), [])):
        quest_data = gobber.get_entity_data(quest)
        # check start_condition and quest status
        if (
            gobber.run_effect(quest_data["start_condition"], quest)
            and gobber.entity_states[quest].variables.get("status") == "idle"
        ):
            options.append(
                {
                    "text": quest_data["start_line"],
                    "effect": (
                        f"gobber.entity_states[gobber.quest_triggers['{str(location_entity)}'][{i}]].variables['status']='inprogress'; "
                        f"gobber.entity_states[gobber.quest_triggers['{str(location_entity)}'][{i}]].state='{quest_data['start_state']}'; "
                        f"gobber.entity_states[gobber.quest_triggers['{str(location_entity)}'][{i}]].step = 0; "
                        f"gobber.entity_stack.append(gobber.quest_triggers['{str(location_entity)}'][{i}])"
                    ),
                }
            )

    for i, character in enumerate(
        gobber.character_locations.get(location_entity[1], [])
    ):
        character_data = gobber.get_entity_data(character)

        logger.info(gobber.run_effect("character_death_msg", character))
        logger.info(gobber.run_effect("character_health", character))
        logger.info(gobber.run_effect("character_name", character))

        options.append(
            {
                "text": random.choice(
                    gobber.get_player_data()["dialogues"]["characters"]["interact"]
                    if gobber.run_effect("len(character_death_msg) == 0", character)
                    else gobber.get_player_data()["dialogues"]["characters"][
                        "find_location"
                    ]
                ).format(character_name=character_data["name"]),
                "effect": f"introduce_character(gobber.character_locations.get('{location_entity[1]}', [])[{i}])",
            }
        )

    for connection in gobber.travel_paths[location_entity]:

        options.append(
            {
                "text": gobber.get_entity_data(connection)["action"],
                "effect": f"gobber.entity_stack.pop(); tread_connection(gobber.EntityID(('connection', '{connection[1]}')))",
            }
        )

    return options


async def _ask_player(options):
    if options != None:
        choice = await _send_option([option["text"] for option in options])
        selected_choice = options[choice]

        if "retrospective" in selected_choice:
            ret = selected_choice["retrospective"]
            if ret["type"] == "story":
                await _send_story(ret["line"])
            elif ret["type"] == "dialogue":
                await _send_dialogue(gobber.get_player_state()["name"], ret["line"])
            elif ret["type"] == "skip":
                pass
        else:
            await _send_dialogue(
                gobber.get_player_state()["name"], selected_choice["text"]
            )

        return selected_choice

    return {}


def load_entity(entity: gobber.EntityID):
    opening_state = random.choice(
        gobber.get_entity_data(entity).get("opening_states", ["__menu__"])
    )
    gobber.entity_states[entity].state = opening_state
    gobber.entity_states[entity].step = 0
    gobber.entity_stack.append(entity)


def introduce_character(character: gobber.EntityID):
    assert character[0] == "character"

    return load_entity(character)

    opening_state = random.choice(
        gobber.get_entity_data(character).get("opening_states", ["__menu__"])
    )
    gobber.entity_states[character].state = opening_state
    gobber.entity_states[character].step = 0
    gobber.entity_stack.append(character)


def reveal_location(location: gobber.EntityID):
    assert location[0] == "location"

    return load_entity(location)

    opening_state = random.choice(
        gobber.get_entity_data(location).get("opening_states", ["__menu__"])
    )
    gobber.entity_states[location].state = opening_state
    gobber.entity_states[location].step = 0
    gobber.entity_stack.append(location)


def tread_connection(connection: gobber.EntityID):
    assert connection[0] == "connection"

    return load_entity(connection)


async def handles_this(current_entity: gobber.EntityID):
    if current_entity[0] == "character":
        return True
    if current_entity[0] == "location":
        return True
    if current_entity[0] == "quest":
        return True
    if current_entity[0] == "connection":
        return True

    await stormfly.leave()
    stormfly.to_mount.clear()

    return False


async def draw_this(current_entity: gobber.EntityID) -> NoReturn:
    state = gobber.entity_states[current_entity]

    # quick local cache for repeated reads
    entity_file = gobber.get_entity_data(current_entity)

    # We can never talk to a dead character
    if current_entity[0] == "character":
        if gobber.run_effect("len(character_death_msg) != 0", current_entity):
            await _send_story(
                str(gobber.run_effect("character_death_msg", current_entity))
            )
            await _send_option(["Continue"])
            gobber.entity_stack.pop()
            await render_state()

    if current_entity[0] == "character" and state.state == "__menu__":
        character_line = random.choice(entity_file["menu_lines"])
        character_name = entity_file["name"]

        options = _character_talk_to_player(current_entity)

        await _send_dialogue(character_name, character_line)
        selected_choice = await _ask_player(options)
        exec(selected_choice.get("effect", "None"), globals(), locals())
        await render_state()
        exit_game()

    if current_entity[0] == "location" and state.state == "__menu__":
        location_ambient = random.choice(entity_file["ambient"])

        options = _location_world_to_player(current_entity)

        await _send_story(location_ambient)

        logger.info(options)

        selected_choice = await _ask_player(options)

        exec(selected_choice.get("effect", "None"), globals(), locals())
        await render_state()
        exit_game()

    if current_entity[0] == "connection" and state.state == "__menu__":
        gobber.entity_stack.pop()
        reveal_location(
            gobber.EntityID(("location", gobber.get_entity_data(current_entity)["to"]))
        )
        await render_state()
        exit_game()

    current_state = entity_file["states"][state.state]
    step = current_state["steps"][state.step]
    steps: int = len(current_state["steps"])

    match step["type"]:
        case "story":
            await _send_story(step["text"])
        case "dialogue":
            speaker = step["speaker"]
            speaker_name = gobber.get_entity_data(
                gobber.EntityID(("character", speaker))
            )["name"]

            await _send_dialogue(speaker_name, step["text"])
            selected_choice = await _ask_player(step.get("choices", None))
            gobber.run_effect(selected_choice.get("effect", "None"), current_entity)
        case "stateUpdate":
            gobber.run_effect(step["update"], current_entity)

    if state.step < (steps - 1):
        gobber.entity_states[current_entity].step += 1
        await render_state()
        asyncio.get_event_loop().stop()
        return
    else:
        # quest completion cleanup
        if current_entity[0] == "quest" and gobber.entity_states[
            current_entity
        ].variables.get("status") in ["completed", "failed"]:
            gobber.entity_stack.pop()
            if len(gobber.entity_stack):
                await render_state()
                asyncio.get_event_loop().stop()
                return
            else:
                logger.debug("No more scenes to render!")
                await exit_game()

        # Move transition
        for transition in current_state.get("transitions", []):
            logger.info(transition["condition"])
            if gobber.run_effect(transition["condition"], current_entity):
                gobber.entity_states[current_entity].state = transition["target"]
                gobber.entity_states[current_entity].step = 0
                await render_state()
                exit_game()

        raise Exception("ERROR: OUT OF TRANSITION TARGETS!!!")


async def render_state() -> NoReturn:
    raise Exception("ERROR: Render_state not defiend")
