from gobber import (
    get_entity_data,
    EntityID,
    quest_triggers,
    run_effect,
    entity_states,
    get_player_data,
    get_player_state,
    entity_stack,
)
import random
import stoick
from typing import NoReturn
import random
import asyncio

from ruffnut import logger
from tuffnut import exit_game
from gobber import (
    get_entity_data,
    run_effect,
    EntityID,
    quest_triggers,
    entity_stack,
    entity_states,
)


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
        if (
            run_effect(quest_data["start_condition"], quest)
            and entity_states[quest].variables.get("status") == "idle"
        ):
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
    player_farewell = random.choice(
        get_player_data()["dialogues"]["characters"]["farewell"]
    )
    options.append(
        {
            "text": player_farewell.format(character_name=char_data["name"]),
            "effect": "entity_stack.pop()",
        }
    )

    return options


async def display_menu_options(character, line, options):
    await stoick.renderer.send_dialogue(character, line)
    if options != None:
        choice = await stoick.renderer.send_option(
            [option["text"] for option in options]
        )
        selected_choice = options[choice]

        if "retrospective" in selected_choice:
            ret = selected_choice["retrospective"]
            if ret["type"] == "story":
                await stoick.renderer.send_story(ret["line"])
            if ret["type"] == "dialogue":
                await stoick.renderer.send_dialogue(
                    get_player_state()["name"], ret["line"]
                )

        return selected_choice

    return {}


def character_interact(character: EntityID):
    assert character[0] == "character"
    global entity_stack, entity_states  # fixed duplicate name in original

    opening_state = random.choice(
        get_entity_data(character.get_file()).get("opening_states", ["__menu__"])
    )
    entity_states[character].state = opening_state
    entity_states[character].step = 0
    entity_stack.append(character)


def handles_this(current_entity: EntityID):
    if current_entity[0] == "character":
        return True
    if current_entity[0] == "location":
        return True
    if current_entity[0] == "quest":
        return True

    return False


async def draw_this(current_entity: EntityID) -> NoReturn:
    global entity_states, entity_stack, quest_triggers

    state = entity_states[current_entity]

    # quick local cache for repeated reads
    entity_file = get_entity_data(current_entity.get_file())

    if current_entity[0] == "character" and state.state == "__menu__":
        character_line = random.choice(entity_file["menu_lines"])
        character_name = entity_file["name"]

        options = build_character_menu_options(current_entity)

        selected_choice = await display_menu_options(
            character_name, character_line, options
        )
        exec(selected_choice.get("effect", "None"), globals(), locals())
        await render_state()
        exit_game()

    if current_entity[0] == "location":
        location_ambient = random.choice(entity_file["ambient"])

        await stoick.renderer.send_story(location_ambient)

    current_state = entity_file["states"][state.state]
    step = current_state["steps"][state.step]
    steps: int = len(current_state["steps"])

    match step["type"]:
        case "story":
            await stoick.renderer.send_story(step["text"])
        case "dialogue":
            speaker = step["speaker"]
            speaker_name = get_entity_data(EntityID(("character", speaker)).get_file())[
                "name"
            ]
            selected_choice = await display_menu_options(
                speaker_name, step["text"], step.get("choices", None)
            )
            run_effect(selected_choice.get("effect", "None"), current_entity)
        case "stateUpdate":
            run_effect(step["update"], current_entity)

    if state.step < (steps - 1):
        entity_states[current_entity].step += 1
        await render_state()
        asyncio.get_event_loop().stop()
        return
    else:
        # quest completion cleanup
        if current_entity[0] == "quest" and entity_states[current_entity].variables.get(
            "status"
        ) in ["completed", "failed"]:
            entity_stack.pop()
            if len(entity_stack):
                await render_state()
                asyncio.get_event_loop().stop()
                return
            else:
                logger.debug("No more scenes to render!")
                await exit_game()

        # Move transition
        for transition in current_state.get("transitions", []):
            logger.info(transition["condition"])
            if run_effect(transition["condition"], current_entity):
                entity_states[current_entity].state = transition["target"]
                entity_states[current_entity].step = 0
                await render_state()
                exit_game()

        raise Exception("ERROR: OUT OF TRANSITION TARGETS!!!")


async def render_state() -> NoReturn:
    raise Exception("ERROR: Render_state not defiend")
