from typing import NoReturn
import asyncio

import gobber

async def exit_game() -> NoReturn:
    if gobber.viking_file != "":
        gobber.save_game_state()
    asyncio.get_event_loop().stop()
    while True:
        await asyncio.sleep(0)
