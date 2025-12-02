from typing import NoReturn
import uuid
import asyncio

from ruffnut import logger
import astrid
import gobber
import stoick


def handles_this(current_entity: gobber.EntityID):
    if current_entity[0] == "init":
        return True

    return False


async def draw_this(current_entity: gobber.EntityID):
    if current_entity[0] == "init" and current_entity[1] == "start_screen":
        await stoick.renderer.send_game_start()
        gobber.entity_stack.append(gobber.EntityID(("init", "viking_select")))
        await render_state()
    elif current_entity[0] == "init" and current_entity[1] == "viking_select":
        vikings_list = gobber.list_vikings()
        viking_idx = await stoick.renderer.send_viking_select(vikings_list)
        print(viking_idx)

        if viking_idx == -1:
            gobber.entity_stack.pop()
            print("GOIN BACK")
            await render_state()
        elif viking_idx == len(vikings_list):
            gobber.entity_stack.append(gobber.EntityID(("init", "viking_create")))
            await render_state()
        else:
            gobber.set_player_file(vikings_list[viking_idx][2])
            print(viking_idx, vikings_list[viking_idx])
            gobber.load_game_state()
            gobber.preload_story_entities()
            await asyncio.sleep(0)
            await stoick.renderer.clear_screen(ask=False)
            stoick.renderer.log(stoick.renderer.dialogue_container.children)
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

            astrid.reveal_location(gobber.EntityID(("location", "berk_square")))
            gobber.save_game_state()
            await render_state()


async def render_state() -> NoReturn:
    raise Exception("ERROR: Render_state not defiend")
