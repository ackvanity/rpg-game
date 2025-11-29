print("RPG Game Main Module")
print("Work in progress...")
print("Except jittery experiences")

from typing import NoReturn
import stoick
import asyncio

from ruffnut import logger
from tuffnut import exit_game
import astrid
from gobber import (
    EntityID,
    quest_triggers,
    entity_stack,
    entity_states,
    preload_story_entities,
)


async def render_state() -> NoReturn:
    global entity_states, entity_stack, quest_triggers

    await asyncio.sleep(0)  # Yield to event loop

    if len(entity_stack) == 0:
        await exit_game()

    current_entity = entity_stack[-1]

    if astrid.handles_this(current_entity):
        await astrid.draw_this(current_entity)

    raise Exception("Current state not implemented!")


def print(*args, **kwargs):
    raise Exception("Non-rendering systems must use interfaced I/O methods")


def input(*args, **kwargs):
    raise Exception("Non-rendering systems must use interfaced I/O methods")


logger.info("Loading entities")
preload_story_entities()

astrid.character_interact(EntityID(("character", "hiccup")))
astrid.render_state = render_state

stoick.renderer = stoick.UrwidTextRenderer(exit_game)
stoick.renderer.callback_asyncio = render_state
stoick.renderer.start()
