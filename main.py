from typing import Any
import asteval
import json

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


entity_states: dict[EntityID, EntityState] = {}

entity_stack: list[EntityID] = [
    EntityID(("quest", "rescue_hiccup_toothless")),
]


def get_entity_data(path: str):
    with open(path, "r") as f:
        return json.load(f)


def load_entity(entity: EntityID):
    global entity_states
    character_data = get_entity_data(entity.get_file())
    entity_states[entity] = EntityState("idle", character_data.get("variables", {}))


print("Loading characters...")

load_entity(EntityID(("character", "hiccup")))
load_entity(EntityID(("character", "toothless")))
load_entity(EntityID(("character", "astrid")))
load_entity(EntityID(("quest", "rescue_hiccup_toothless")))

entity_states[EntityID(("quest", "rescue_hiccup_toothless"))].state = "travel_to_crash"
entity_states[EntityID(("quest", "rescue_hiccup_toothless"))].step = 1

print(entity_states)

def run_effect(effect: str, entity: EntityID):
    aeval = asteval.Interpreter()

    # Self entity state
    for var, value in entity_states[entity].variables.items():
        aeval.symtable[f"{entity[0]}_{var}"] = value
    
    # Referenced character states
    for character_name in get_entity_data(entity.get_file()).get("characters", {}).keys():
        character_entity = EntityID(("character", character_name))
        for var, value in entity_states[character_entity].variables.items():
            aeval.symtable[f"{character_name}_{var}"] = value

    result = aeval(effect)

    # Self entity state
    for var, value in entity_states[entity].variables.items():
        entity_states[entity].variables[var] = aeval.symtable[f"{entity[0]}_{var}"] = value
    
    # Referenced character states
    for character_name in get_entity_data(entity.get_file()).get("characters", {}).keys():
        character_entity = EntityID(("character", character_name))
        for var, value in entity_states[character_entity].variables.items():
            aeval.symtable[f"{character_name}_{var}"] = value

def render_state():
    global entity_states, entity_stack
    current_entity = entity_stack[-1]
    state = entity_states[current_entity]

    step = get_entity_data(current_entity.get_file())["states"][state.state]["steps"][
        state.step
    ]

    match step["type"]:
        case "story":
            print(step["text"])
        case "dialogue":
            speaker = step["speaker"]
            speaker_name = get_entity_data(EntityID(("character", speaker)).get_file())[
                "name"
            ]
            print(f"{speaker_name}: {step['text']}")
            if "choices" in step:
                for i, choice in enumerate(step["choices"]):
                    print(f"{i + 1}. {choice['text']}")
                choice = int(input("Choose an choice: ")) - 1
                selected_choice = step["choices"][choice]

                print(
                    f"You selected: {selected_choice['text']}; Effect: {selected_choice.get('effect', 'None')}"
                )


render_state()
