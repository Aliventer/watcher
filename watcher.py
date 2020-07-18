from datetime import datetime
import json
import discord
import heapq
from typing import Dict, List, Optional, Tuple


class Watcher:
    """A storage for per-member time records"""
    def __init__(self, total_time: Optional[Dict[int, datetime]] = None):
        self._total_time = total_time or {}
        self._active_sessions = {}

    @classmethod
    def from_file(cls, filename: str):
        with open(filename, 'r', encoding='utf-8') as f:
            time_data = json.load(f)
        # Converting member IDs into ints
        # and time strings into time
        total_time = {int(k): datetime.fromisoformat(v) for k, v in time_data.items()}
        return cls(total_time=total_time)

    def exists(self, member: discord.Member) -> bool:
        """Indicates if the member have their voice session
        """
        return self._active_sessions.get(member.id) is not None

    def _start_session(self, member_id: int):
        self._active_sessions[member_id] = datetime.now()

    def _stop_session(self, member_id: int):
        session_time = datetime.now() - self._active_sessions.pop(member_id)
        self._total_time[member_id] = self._total_time.get(member_id, datetime.min) + session_time

    def _populate_sessions(self, member_ids):
        for member_id in member_ids:
            self._start_session(member_id)

    def start_session(self, member: discord.Member):
        """Safely start member's voice session

        Will gracefully stop member's previous
        voice session (if any) before starting new one.
        """
        self.stop_session(member)
        self._start_session(member.id)

    def stop_session(self, member: discord.Member):
        """Safely stop member's voice session

        Won't produce any side effect if the member
        currently has no active voice session.
        """
        if self.exists(member):
            self._stop_session(member.id)

    def populate_sessions(self, members: List[discord.Member]):
        """Start voice sessions for multiple members.
        """
        member_ids = map(lambda m: m.id, members)
        self._populate_sessions(member_ids)

    def clear_sessions(self) -> List[int]:
        """Safely stop all active voice sessions

        Returns list of ids of members whose sessions were closed.
        """
        ids = self._active_sessions.copy().keys()
        for member_id in ids:
            self._stop_session(member_id)
        return ids

    def commit(self):
        """Add current session time to the total time for every member
        """
        member_ids = self.clear_sessions()
        self._populate_sessions(member_ids)

    def get_member_time(self, member: discord.Member) -> Optional[datetime]:
        """Get total time record for specified member

        This will stop member's current session (if any) and create a new one.
        """
        if self.exists(member):
            self.start_session(member)
        return self._total_time.get(member.id)

    def get_top_time(self, size: int = 5) -> List[Tuple[int, datetime]]:
        """Get list of top `size` members and their time records

        This will re-create all currently active sessions.
        """
        self.commit()
        # TODO: maybe save current heap from self._total_time for later use?
        return heapq.nlargest(size, self._total_time.items(), key=lambda item: item[1])

    def empty(self):
        """Clear all data in Watcher

        This will clear all sessions as well as total
        time for each member.
        """
        self.clear_sessions()
        self._total_time = {}

    def save(self, filename):
        """Save total time records to the file

        This will stop all currently active voice sessions.
        """
        self.clear_sessions()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self._total_time, f, indent=4, default=str)  # save time in isoformat
