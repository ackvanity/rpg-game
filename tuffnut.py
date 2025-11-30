from typing import Any, NoReturn
import asteval
import json
import random
from pathlib import Path
import logging
from datetime import datetime
from stoick import UrwidTextRenderer as Renderer
import asyncio

import gobber

async def exit_game() -> NoReturn:
    if gobber.viking_file != "":
        gobber.save_game_state()
    asyncio.get_event_loop().stop()
    while True:
        await asyncio.sleep(0)
