import asyncio
from functools import partial

from discord.ext import commands

from config import token


class TimeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='>')
        self.load_extension('time_recorder')

    async def on_ready(self):
        print('Connnected.')

    async def close(self):
        loop = asyncio.get_event_loop()
        func = partial(self.unload_extension, 'time_recorder')
        await loop.run_in_executor(None, func)
        await super().close()


if __name__ == '__main__':
    bot = TimeBot()
    bot.run(token)
