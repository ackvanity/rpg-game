import json

print("RPG Game Main Module")
print("Work in progress...")
print("Except jittery experiences")

class EntityState:
  variables: dict[str, any]
  state: str
  step: int

  def __init__(self, state: str, variables: dict[str, any] | None = None):
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

def render_state():
  global entity_states, entity_stack
  current_entity = entity_stack[-1]
  state = entity_states[current_entity]

  step = get_entity_data(current_entity.get_file())["states"][state.state]["steps"][state.step]

  match step["type"]:
    case "story":
      print(step["text"])
    case "dialogue":
      speaker = step["speaker"]
      speaker_name = get_entity_data(EntityID(( "character", speaker)).get_file())["name"]
      print(f"{speaker_name}: {step['text']}")
      if "choices" in step:
        for i, choice in enumerate(step["choices"]):
          print(f"{i + 1}. {choice['text']}")
        choice = int(input("Choose an choice: ")) - 1
        selected_choice = step["choices"][choice]

        print(f"You selected: {selected_choice['text']}; Effect: {selected_choice.get('effect', 'None')}")

render_state()
