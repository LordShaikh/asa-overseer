"""Snapshot diffing - computes player join/leave and server add/remove events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from core.eos.matchmaking import EOSSession


@dataclass
class PlayerChange:
    player_id: str
    session_id: str
    server_name: str
    joined: bool  # True = joined, False = left


@dataclass
class SnapshotDiff:
    added_servers: List[EOSSession] = field(default_factory=list)
    removed_servers: List[EOSSession] = field(default_factory=list)
    player_changes: List[PlayerChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added_servers or self.removed_servers or self.player_changes)

    @property
    def joined_players(self) -> List[PlayerChange]:
        return [p for p in self.player_changes if p.joined]

    @property
    def left_players(self) -> List[PlayerChange]:
        return [p for p in self.player_changes if not p.joined]


def compute_diff(
    prev: Dict[str, EOSSession],
    current: Dict[str, EOSSession],
) -> SnapshotDiff:
    """Diff two session snapshots and return structured changes."""
    diff = SnapshotDiff()

    prev_ids = set(prev.keys())
    curr_ids = set(current.keys())

    # New servers
    for sid in curr_ids - prev_ids:
        diff.added_servers.append(current[sid])

    # Removed servers
    for sid in prev_ids - curr_ids:
        diff.removed_servers.append(prev[sid])

    # Player changes on persisting servers
    for sid in prev_ids & curr_ids:
        prev_sess = prev[sid]
        curr_sess = current[sid]
        prev_players: Set[str] = set(prev_sess.player_ids)
        curr_players: Set[str] = set(curr_sess.player_ids)

        for pid in curr_players - prev_players:
            diff.player_changes.append(
                PlayerChange(
                    player_id=pid,
                    session_id=sid,
                    server_name=curr_sess.server_name,
                    joined=True,
                )
            )
        for pid in prev_players - curr_players:
            diff.player_changes.append(
                PlayerChange(
                    player_id=pid,
                    session_id=sid,
                    server_name=curr_sess.server_name,
                    joined=False,
                )
            )

    return diff
