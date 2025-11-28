from typing import Any
import asteval
import json
import random
from pathlib import Path
import logging
from datetime import datetime
from stoick import UrwidTextRenderer as Renderer
import asyncio

# Configure logging once, early in your main module
log_file = f"logs/game_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    filename=log_file,
    filemode="w",
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("GameLogger")

print("RPG Game Main Module")
print("Work in progress...")
print("Except jittery experiences")

class EntityState:
    variables: dict[str, Any]
    state: str
    step: int

    def __init__(self, state: str, variables: dict[str, Any] | None = None):
        self.state = state
        self.step = 0
        self.variables = variables if variables is not None else {}

    def __str__(self):
        return f"EntityState(state={self.state}, step={self.step}, variables={self.variables})"

    def __repr__(self):
        return self.__str__()

class EntityID(tuple[str, str]):
    def get_file(self) -> str:
        return f"story/{self[0]}/{self[1]}.json"

    def __new__(cls, tup: tuple[str, str]):
        return super(EntityID, cls).__new__(cls, tup)

    def __eq__(self, other):
        if not isinstance(other, EntityID):
            return False
        return self[0] == other[0] and self[1] == other[1]

    def __hash__(self):
        return hash((self[0], self[1]))

    def __str__(self):
        return f"{self[0]}:{self[1]}"

    def __repr__(self):
        return self.__str__()


def get_entity_data(path: str):
    with open(path, "r") as f:
        return json.load(f)


def get_player_data():
    with open("story/player.json", "r") as f:
        return json.load(f)


def get_player_state():
    with open("savegame.json", "r") as f:
        return json.load(f)


def load_entity(entity: EntityID):
    global entity_states, quest_triggers, character_locations
    character_data = get_entity_data(entity.get_file())
    entity_states[entity] = EntityState("idle", character_data.get("variables", {}))

    if entity[0] == "quest":
        entity_states[entity].variables["status"] = "idle"
        quest_triggers[get_entity_data(entity.get_file())["start_character"]] = (
            quest_triggers.get(
                get_entity_data(entity.get_file())["start_character"], []
            )
        )
        quest_triggers[get_entity_data(entity.get_file())["start_character"]].append(
            entity
        )

    if entity[0] == "character":
        character_locations[get_entity_data(entity.get_file())["location"]] = (
            character_locations.get(get_entity_data(entity.get_file())["location"], [])
        )
        character_locations[get_entity_data(entity.get_file())["location"]].append(
            entity
        )


def preload_story_entities(base_path="story"):
    """
    Preload all entities from story/*/*.json using load_entity().
    The base_path is relative to the current working directory by default.
    """
    base_dir = Path(base_path)
    if not base_dir.exists():
        raise FileNotFoundError(f"Story base path not found: {base_dir}")

    count = 0
    for type_dir in base_dir.iterdir():
        if not type_dir.is_dir():
            continue
        for file_path in type_dir.glob("*.json"):
            entity_type = type_dir.name
            entity_name = file_path.stem  # filename without .json
            if entity_type == "location" and entity_name == "connections":
                continue

            load_entity(EntityID((entity_type, entity_name)))
            count += 1

    logger.info(f"Preloaded {count} story entities from '{base_path}'.")


def run_effect(effect: str, entity: EntityID):
    aeval = asteval.Interpreter()

    # Self entity state
    for var, value in entity_states[entity].variables.items():
        aeval.symtable[f"{entity[0]}_{var}"] = value

    # Referenced character states
    for character_name in (
        get_entity_data(entity.get_file()).get("characters", {}).keys()
    ):
        character_entity = EntityID(("character", character_name))
        for var, value in entity_states[character_entity].variables.items():
            aeval.symtable[f"{character_name}_{var}"] = value

    result = aeval(effect)

    # Self entity state
    for var, value in entity_states[entity].variables.items():
        entity_states[entity].variables[var] = aeval.symtable[f"{entity[0]}_{var}"]

    # Referenced character states
    for character_name in (
        get_entity_data(entity.get_file()).get("characters", {}).keys()
    ):
        character_entity = EntityID(("character", character_name))
        for var, value in entity_states[character_entity].variables.items():
            entity_states[character_entity].variables[var] = aeval.symtable[
                f"{character_name}_{var}"
            ]

    return result


async def render_state():
    global entity_states, entity_stack, quest_triggers, renderer
    
    await asyncio.sleep(0)  # Yield to event loop

    if len(entity_stack) == 0:
        return

    current_entity = entity_stack[-1]
    state = entity_states[current_entity]

    if current_entity[0] == "character" and state.state == "__menu__":
        character_line = random.choice(
            get_entity_data(current_entity.get_file())["menu_lines"]
        )
        character_name = get_entity_data(current_entity.get_file())["name"]
        character_code = current_entity[1]

        def transition_state(option):
            option["effect"] = (
                f"entity_states[entity_stack[-1]].state = '{option['state']}'; entity_stack[-1].step = 0"
            )
            return option

        options = list(
            map(
                transition_state,
                get_entity_data(current_entity.get_file())["option_menus"],
            )
        )

        for i, quest in enumerate(quest_triggers[character_code]):
            if (
                run_effect(get_entity_data(quest.get_file())["start_condition"], quest)
                and entity_states[quest].variables["status"] == "idle"
            ):
                options.append(
                    {
                        "text": get_entity_data(quest.get_file())["start_line"],
                        "effect": f"entity_states[quest_triggers[character_code][{i}]].variables['status']='inprogress'; entity_states[quest_triggers[character_code][{i}]].state='{get_entity_data(quest.get_file())['start_state']}'; entity_states[quest_triggers[character_code][{i}]].step = 0; entity_stack.append(quest_triggers[character_code][{i}])",
                    }
                )

        options.append(
            {
                "text": random.choice(
                    get_player_data()["dialogues"]["characters"]["farewell"]
                ).format(character_name=character_name),
                "effect": f"entity_stack.pop()",
            }
        )

        await renderer.send_dialogue(character_name, character_line)

        choice = await renderer.send_option(list(map(lambda x: x["text"], options)))
        selected_choice = options[choice]
        exec(selected_choice.get("effect", "None"), globals(), locals())
        await render_state()
        return
    if current_entity[0] == "location":
        location_ambient = random.choice(
            get_entity_data(current_entity.get_file())["ambient"]
        )

    current_state = get_entity_data(current_entity.get_file())["states"][state.state]

    step = current_state["steps"][state.step]

    steps: int = len(current_state["steps"])

    match step["type"]:
        case "story":
            await renderer.send_story(step["text"])
        case "dialogue":
            speaker = step["speaker"]
            speaker_name = get_entity_data(EntityID(("character", speaker)).get_file())[
                "name"
            ]
            await renderer.send_dialogue(speaker_name, step["text"].format(player_name=get_player_state()["name"]))
            if "choices" in step:
                choice = await renderer.send_option(
                    list(map(lambda x: x["text"], step["choices"]))
                )

                selected_choice = step["choices"][choice]
                run_effect(selected_choice.get("effect", "None"), current_entity)

                if "retrospective" in step["choices"][choice]:
                    if step["choices"][choice]["retrospective"]["type"] == "story":
                        await renderer.send_story(step["choices"][choice]["retrospective"]["line"])
                    if step["choices"][choice]["retrospective"]["type"] == "dialogue":
                        await renderer.send_dialogue(get_player_state()["name"], step["choices"][choice]["retrospective"]["line"])

        case "stateUpdate":
            run_effect(step["update"], current_entity)

    if state.step < (steps - 1):
        entity_states[current_entity].step += 1
        return await render_state()
    else:
        if current_entity[0] == "quest" and entity_states[current_entity].variables[
            "status"
        ] in ["completed", "failed"]:
            entity_stack.pop()

            if len(entity_stack):
                return await render_state()
            else:
                logger.debug("No more scenes to render!")
                exit()

        # Move transition
        for transition in current_state["transitions"]:
            if run_effect(transition["condition"], current_entity):
                entity_states[current_entity].state = transition[
                    "target"
                ]  # TODO: Tell Stormfly to enforce valid target names
                entity_states[current_entity].step = (
                    0  # TODO: Tell Stormfly to disallow empty states
                )
                return await render_state()

        raise Exception("ERROR: OUT OF TRANSITION TARGETS!!!")


def character_interact(character: EntityID):
    assert character[0] == "character"
    global entity_stack, entity_stack

    opening_state = random.choice(
        get_entity_data(character.get_file()).get("opening_states", ["__menu__"])
    )
    entity_states[character].state = opening_state
    entity_states[character].step = 0
    entity_stack.append(character)


entity_states: dict[EntityID, EntityState] = {}
entity_stack: list[EntityID] = []
quest_triggers: dict[str, list[EntityID]] = {}
character_locations: dict[str, list[EntityID]] = {}


def print(*args, **kwargs):
    raise Exception("Non-rendering systems must use interfaced I/O methods")


def input(*args, **kwargs):
    raise Exception("Non-rendering systems must use interfaced I/O methods")


logger.info("Loading entities")
preload_story_entities()

character_interact(EntityID(("character", "hiccup")))

renderer = Renderer(callback_asyncio=render_state)
renderer.start()

