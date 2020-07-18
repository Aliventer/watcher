import asyncio
from functools import partial
from itertools import chain

from discord.ext import commands, tasks
import discord

from watcher import Watcher

TIME_RECORD_SAVE_FILE = 'time_data.json'
# This emojis will be concatenated with the user name
# according to their place in time top like so:
#                  1              2             3            4+
#                 v              v             v             v
TOP_EMOJI = ('\U0001f947', '\U0001f948', '\U0001f949', '\U0001f3c5')


class TimeRecorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watcher = Watcher.from_file(TIME_RECORD_SAVE_FILE)
        self.cleaner.start()

    def cog_unload(self):
        self.cleaner.cancel()
        self.watcher.save(TIME_RECORD_SAVE_FILE)

    @staticmethod
    def is_active(state: discord.VoiceState) -> bool:
        return state.channel and not state.afk and not state.self_mute and not state.mute

    @staticmethod
    def time_fmt(time_record):
        return f'{time_record.hour:02n}:{time_record.minute:02n}:{time_record.second:02n}'

    @tasks.loop(hours=24)
    async def cleaner(self):
        self.watcher.empty()
        await self.run_populator()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.run_populator()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.is_active(before) and self.is_active(after):
            self.watcher.start_session(member)
        elif self.is_active(before) and not self.is_active(after):
            self.watcher.stop_session(member)

    async def run_populator(self):
        voice_channels = chain.from_iterable(guild.voice_channels for guild in self.bot.guilds)
        members = chain.from_iterable(vc.members for vc in voice_channels)
        active_members = filter(lambda m: self.is_active(m.voice), members)

        loop = asyncio.get_event_loop()
        func = partial(self.watcher.populate_sessions, active_members)
        await loop.run_in_executor(None, func)

    @commands.group(invoke_without_command=True)
    async def time(self, ctx, user: discord.User = None):
        user = user or ctx.author
        time_record = self.watcher.get_member_time(user)
        if time_record is None:
            await ctx.send(f'We haven\'t seen {user} today...')
            return
        await ctx.send(self.time_fmt(time_record))

    @time.command(name='top')
    async def time_top(self, ctx):
        time_records = self.watcher.get_top_time(size=5)
        em = discord.Embed(colour=discord.Colour.blurple())
        for i, item in enumerate(time_records):
            member_id, time_record = item
            emoji = TOP_EMOJI[i] if i < len(TOP_EMOJI) - 1 else TOP_EMOJI[-1]
            user = self.bot.get_user(member_id)
            em.add_field(name=f'{emoji} {user}', value=self.time_fmt(time_record))
        await ctx.send(embed=em)


def setup(bot):
    time_recorder = TimeRecorder(bot)
    bot.add_cog(time_recorder)
