print("RPG Game Main Module")
print("Work in progress...")
print("Except jittery experiences")

from typing import NoReturn
import stoick
import asyncio

from ruffnut import logger
from tuffnut import exit_game
import astrid
import gobber
import ack


async def render_state() -> NoReturn:
    global entity_states, entity_stack, quest_triggers

    await asyncio.sleep(0)  # Yield to event loop

    if len(gobber.entity_stack) == 0:
        await exit_game()

    current_entity = gobber.entity_stack[-1]

    if astrid.handles_this(current_entity):
        await astrid.draw_this(current_entity)
    elif ack.handles_this(current_entity):
        await ack.draw_this(current_entity)

    raise Exception("Current state not implemented!")


def print(*args, **kwargs):
    raise Exception("Non-rendering systems must use interfaced I/O methods")


def input(*args, **kwargs):
    raise Exception("Non-rendering systems must use interfaced I/O methods")


logger.info("Loading entities")
gobber.preload_story_entities()

# astrid.introduce_character(EntityID(("character", "hiccup")))
# astrid.reveal_location(gobber.EntityID(("location", "berk_square")))

gobber.entity_stack = [gobber.EntityID(("init", "start_screen"))]
astrid.render_state = render_state
ack.render_state = render_state

stoick.renderer = stoick.UrwidTextRenderer(exit_game)
stoick.renderer.callback_asyncio = render_state
stoick.renderer.start()
