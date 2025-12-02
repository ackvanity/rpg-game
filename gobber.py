from typing import Any
import asteval
import json
from pathlib import Path
from os import listdir
from os.path import isfile, join

from ruffnut import logger

SAVEGAME_FOLDER = "savegames"


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

def list_vikings():
    save_files = [
        f for f in listdir(SAVEGAME_FOLDER) if isfile(join(SAVEGAME_FOLDER, f))
    ]

    vikings_list = []

    for save_file in save_files:
        state = get_player_state(SAVEGAME_FOLDER + "/" + save_file)
        name = state["name"]
        fullname = state["fullname"]
        vikings_list.append((name, fullname, save_file))

    return vikings_list


def get_entity_data(entity: EntityID):
    file = entity.get_file()
    if entity[0] == "connection":
        file = EntityID(("location", "connections")).get_file()
    with open(file, "r") as f:
        if entity[0] == "connection":
            return json.load(f)[entity[1]]

        return json.load(f)


def get_player_data():
    with open("story/player.json", "r") as f:
        return json.load(f)


def get_player_state(filename=None):
    if filename == None:
        filename = viking_file

    if filename == None:
        raise Exception("No file to open!")

    with open(filename, "r") as f:  # type: ignore
        return json.load(f)


def set_player_file(filename):
    global viking_file
    viking_file = SAVEGAME_FOLDER + "/" + filename


def set_player_state(obj):
    with open(viking_file, "w") as f:
        return json.dump(obj, f)


def load_entity(entity: EntityID):
    global entity_states, quest_triggers, character_locations
    character_data = get_entity_data(entity)
    if entity not in entity_states:
        entity_states[entity] = EntityState("idle", character_data.get("variables", {}))
    else:
        for k, v in character_data.get("variables", {}).items():
            entity_states[entity].variables.setdefault(k, v)

    if entity[0] == "quest":
        entity_states[entity].variables.setdefault("status", "idle")
        quest_triggers[get_entity_data(entity)["start_entity"]] = (
            quest_triggers.get(get_entity_data(entity)["start_entity"], [])
        )
        if (
            entity
            not in quest_triggers[get_entity_data(entity)["start_entity"]]
        ):
            quest_triggers[get_entity_data(entity)["start_entity"]].append(
                entity
            )

    if entity[0] == "character":
        entity_states[entity].variables.setdefault("death_msg", "")
        character_locations[entity_states[entity].variables["location"]] = (
            character_locations.get(entity_states[entity].variables["location"], [])
        )
        if (
            entity
            not in character_locations[entity_states[entity].variables["location"]]
        ):
            character_locations[entity_states[entity].variables["location"]].append(
                entity
            )

def load_connections(file: str):
    with open(file, "r") as f:
        connections = json.load(f)
        for id, data in connections.items():
            entity = EntityID(("connection", id))
            load_entity(entity)

            travel_paths[EntityID(("location", data["from"]))] = travel_paths.get(EntityID(("location", data["from"])), [])
            travel_paths[EntityID(("location", data["from"]))].append(entity)


def load_game_state():
    """
    Replace current entity_states and entity_stack with data parsed from JSON string s.
    """
    global entity_states, entity_stack
    obj = get_player_state()
    logger.info(obj)
    new_states: dict[EntityID, EntityState] = {}
    for entry in obj.get("entity_states", []):
        eid = EntityID((entry["type"], entry["name"]))
        est = EntityState(entry.get("state", "idle"), entry.get("variables", {}))
        est.step = int(entry.get("step", 0))
        new_states[eid] = est

    entity_states = new_states
    entity_stack = [
        EntityID((e["type"], e["name"])) for e in obj.get("entity_stack", [])
    ]


def save_game_state():
    """
    Saves current entity_states and entity_stack into game save file.
    """
    obj = get_player_state()

    obj["entity_states"] = [
        {
            "type": eid[0],
            "name": eid[1],
            "state": est.state,
            "step": est.step,
            "variables": est.variables,
        }
        for eid, est in entity_states.items()
    ]

    obj["entity_stack"] = [{"type": e[0], "name": e[1]} for e in entity_stack]

    logger.info(obj)

    set_player_state(obj)


def preload_story_entities(base_path="story", report=load_entity):
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
                load_connections(EntityID((entity_type, entity_name)).get_file())
            else:
                report(EntityID((entity_type, entity_name)))
                count += 1

    logger.info(f"Preloaded {count} story entities from '{base_path}'.")


def run_effect(effect: str, entity: EntityID):
    aeval = asteval.Interpreter()

    # Self entity state
    for var, value in entity_states[entity].variables.items():
        aeval.symtable[f"{entity[0]}_{var}"] = value

    # Referenced character states
    for character_name in (
        get_entity_data(entity).get("characters", {}).keys()
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
        get_entity_data(entity).get("characters", {}).keys()
    ):
        character_entity = EntityID(("character", character_name))
        for var, value in entity_states[character_entity].variables.items():
            entity_states[character_entity].variables[var] = aeval.symtable[
                f"{character_name}_{var}"
            ]

    return result


entity_states: dict[EntityID, EntityState] = {}
entity_stack: list[EntityID] = []
quest_triggers: dict[str, list[EntityID]] = {}
character_locations: dict[str, list[EntityID]] = {}
travel_paths: dict[EntityID, list[EntityID]] = {}

viking_file: str = None  # type: ignore
