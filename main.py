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


# Refactored run_effect to remove duplication: small helpers for loading/writing the symtable
def run_effect(effect: str, entity: EntityID):
    aeval = asteval.Interpreter()
    entity_file = get_entity_data(entity.get_file())

    # helper: load an entity's variables into the interpreter symtable with prefix "<type>_<var>"
    def _load_entity_to_sym(eid: EntityID):
        for var, value in entity_states[eid].variables.items():
            aeval.symtable[f"{eid[0]}_{var}"] = value

    # helper: write back variables from symtable to the entity state (if present)
    def _write_back_from_sym(eid: EntityID):
        for var in list(entity_states[eid].variables.keys()):
            sym_name = f"{eid[0]}_{var}"
            if sym_name in aeval.symtable:
                entity_states[eid].variables[var] = aeval.symtable[sym_name]

    # load self
    _load_entity_to_sym(entity)

    # load any characters referenced by this entity's file (if any)
    for character_name in entity_file.get("characters", {}).keys():
        char_entity = EntityID(("character", character_name))
        _load_entity_to_sym(char_entity)

    # evaluate
    result = aeval(effect)

    # write back for self and referenced characters
    _write_back_from_sym(entity)
    for character_name in entity_file.get("characters", {}).keys():
        char_entity = EntityID(("character", character_name))
        _write_back_from_sym(char_entity)

    return result


# Helper to build the options for a character's menu (keeps render_state concise)
def build_character_menu_options(character_entity: EntityID):
    char_data = get_entity_data(character_entity.get_file())
    character_code = character_entity[1]

    def transition_state(option):
        # don't mutate original option objects in char files
        opt = option.copy()
        opt["effect"] = (
            f"entity_states[entity_stack[-1]].state = '{opt['state']}'; entity_stack[-1].step = 0"
        )
        return opt

    options = list(map(transition_state, char_data.get("option_menus", [])))

    # Append quests that can start
    for i, quest in enumerate(quest_triggers.get(character_code, [])):
        quest_data = get_entity_data(quest.get_file())
        # check start_condition and quest status
        if run_effect(quest_data["start_condition"], quest) and entity_states[quest].variables.get("status") == "idle":
            options.append(
                {
                    "text": quest_data["start_line"],
                    "effect": (
                        f"entity_states[quest_triggers['{character_code}'][{i}]].variables['status']='inprogress'; "
                        f"entity_states[quest_triggers['{character_code}'][{i}]].state='{quest_data['start_state']}'; "
                        f"entity_states[quest_triggers['{character_code}'][{i}]].step = 0; "
                        f"entity_stack.append(quest_triggers['{character_code}'][{i}])"
                    ),
                }
            )

    # Add farewell option
    player_farewell = random.choice(get_player_data()["dialogues"]["characters"]["farewell"])
    options.append(
        {
            "text": player_farewell.format(character_name=char_data["name"]),
            "effect": "entity_stack.pop()",
        }
    )

    return options

async def render_state():
    global entity_states, entity_stack, quest_triggers, renderer

    await asyncio.sleep(0)  # Yield to event loop

    if len(entity_stack) == 0:
        return

    current_entity = entity_stack[-1]
    state = entity_states[current_entity]

    # quick local cache for repeated reads
    entity_file = get_entity_data(current_entity.get_file())

    # character menu flow (refactored to use helper)
    if current_entity[0] == "character" and state.state == "__menu__":
        character_line = random.choice(entity_file["menu_lines"])
        character_name = entity_file["name"]

        options = build_character_menu_options(current_entity)

        await renderer.send_dialogue(character_name, character_line)
        choice = await renderer.send_option(list(map(lambda x: x["text"], options)))
        selected_choice = options[choice]
        # original code used exec to apply effect strings (keeps dynamic behavior)
        exec(selected_choice.get("effect", "None"), globals(), locals())
        await render_state()
        return

    if current_entity[0] == "location":
        location_ambient = random.choice(entity_file["ambient"])

    current_state = entity_file["states"][state.state]
    step = current_state["steps"][state.step]
    steps: int = len(current_state["steps"])

    match step["type"]:
        case "story":
            await renderer.send_story(step["text"])
        case "dialogue":
            speaker = step["speaker"]
            speaker_name = get_entity_data(EntityID(("character", speaker)).get_file())["name"]
            await renderer.send_dialogue(speaker_name, step["text"].format(player_name=get_player_state()["name"]))
            if "choices" in step:
                choice = await renderer.send_option(list(map(lambda x: x["text"], step["choices"])))
                selected_choice = step["choices"][choice]
                run_effect(selected_choice.get("effect", "None"), current_entity)
                if "retrospective" in selected_choice:
                    ret = selected_choice["retrospective"]
                    if ret["type"] == "story":
                        await renderer.send_story(ret["line"])
                    if ret["type"] == "dialogue":
                        await renderer.send_dialogue(get_player_state()["name"], ret["line"])
        case "stateUpdate":
            run_effect(step["update"], current_entity)

    if state.step < (steps - 1):
        entity_states[current_entity].step += 1
        return await render_state()
    else:
        # quest completion cleanup
        if current_entity[0] == "quest" and entity_states[current_entity].variables.get("status") in ["completed", "failed"]:
            entity_stack.pop()
            if len(entity_stack):
                return await render_state()
            else:
                logger.debug("No more scenes to render!")
                exit()

        # Move transition
        for transition in current_state.get("transitions", []):
            if run_effect(transition["condition"], current_entity):
                entity_states[current_entity].state = transition["target"]
                entity_states[current_entity].step = 0
                return await render_state()

        raise Exception("ERROR: OUT OF TRANSITION TARGETS!!!")

def character_interact(character: EntityID):
    assert character[0] == "character"
    global entity_stack, entity_states  # fixed duplicate name in original

    opening_state = random.choice(get_entity_data(character.get_file()).get("opening_states", ["__menu__"]))
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

