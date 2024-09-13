import ast
from datetime import datetime
from typing import Optional

from asyncpg import Record
from disnake import Member
from harmonize.objects import Track

from utils.basic.services.database import Database, ChisatoPool
from utils.dataclasses.music import CustomPlaylist
from utils.exceptions import MaximumPlaylist, AlreadyCreatedPlaylist, PlaylistNotFound


class MusicDB(Database):
    __slots__ = (
        "bot"
    )

    cluster: str = "music"

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool)
        self.bot = self.this_pool.client

    @staticmethod
    def _serialize_last_track(encoded: str, listened: int) -> tuple[Track, int]:
        return (
            Track.from_encode(encoded), listened
        )

    async def get_last_tracks(self, member: Member) -> list[tuple[Track, int]]:
        return sorted(
            [
                self._serialize_last_track(i[0], i[1]) for i in

                await self.fetchall(
                    "SELECT encoded, listened FROM music_last_listened WHERE user_id = $1 ORDER BY listened",
                    member.id
                )
            ],
            key=lambda x: x[1],
            reverse=True
        )

    async def add_last_track(self, member: Member, track: Track) -> None:
        await self.execute(
            "INSERT INTO music_last_listened (user_id, encoded, listened) VALUES ($1, $2, $3)",
            member.id, track.encoded, datetime.now().timestamp()
        )

    async def _serialize(self, record: Record) -> CustomPlaylist:
        return CustomPlaylist(
            name=record[0],
            id=record[1],
            owner=record[2],
            closed=record[3],
            tracks=[
                Track.from_encode(i)
                for i in await self._get_encodes_from_uids(
                    ast.literal_eval(record[4])
                )
            ],
            listened=record[5]
        )

    async def _get_track_uid(self, encoded: str) -> int:
        await self._add_track(encoded)
        return await self.fetchval(
            "SELECT uid FROM music_tracks WHERE encoded = $1",
            encoded
        )

    async def _get_track_encoded(self, uid: int) -> Optional[str]:
        return await self.fetchval(
            "SELECT encoded FROM music_tracks WHERE uid = $1",
            uid
        )

    async def _add_track(self, encoded: str) -> None:
        await self.execute("SELECT add_track_if_not_exists($1)", encoded)

    async def get_playlist(self, owner: Member, name: str) -> Optional[CustomPlaylist]:
        data = await self.fetchrow(
            "SELECT * FROM music_playlists WHERE name = $1 AND user_id = $2",
            name, owner.id
        )
        if data:
            return await self._serialize(data)

    async def get_playlist_from_uid(self, uid: int) -> Optional[CustomPlaylist]:
        data = await self.fetchrow(
            "SELECT * FROM music_playlists WHERE uid = $1",
            uid
        )
        if not data:
            return

        return await self._serialize(data)

    async def _get_uids_from_encodes(self, encodes: list[str]) -> list[int]:
        if encodes:
            return [
                i[0] for i in

                await self.fetchall(
                    f"""
                    SELECT uid FROM music_tracks
                    WHERE encoded in ({','.join([f'${i}' for i in range(1, len(encodes) + 1)])})
                    """,
                    *encodes
                )
            ]
        return []

    async def _get_encodes_from_uids(self, uids: list[int]) -> list[str]:
        if uids:
            return [
                i[0] for i in

                await self.fetchall(
                    f"""
                    SELECT encoded FROM music_tracks
                    WHERE uid in ({','.join([f'${i}' for i in range(1, len(uids) + 1)])})
                    """,
                    *uids
                )
            ]
        return []

    async def create_playlist(
            self,
            name: str,
            owner: Member,
            closed: bool = False,
            tracks: list[Track] = None
    ) -> CustomPlaylist:
        if (await self.fetchval("SELECT COUNT(*) FROM music_playlists WHERE user_id = $1", owner.id)) >= 5:
            raise MaximumPlaylist

        elif await self.fetchval(
                "SELECT uid FROM music_playlists WHERE name = $1 AND user_id = $2",
                name, owner.id
        ):
            raise AlreadyCreatedPlaylist

        await self.executemany(
            "SELECT add_track_if_not_exists($1)",
            [(i.encoded,) for i in tracks]
        )

        await self.execute(
            """
            INSERT INTO music_playlists (name, user_id, tracks, closed)
            VALUES ($1, $2, $3, $4);
            """,
            name,
            owner.id,
            str(await self._get_uids_from_encodes([i.encoded for i in tracks])),
            closed
        )

        return await self.get_playlist(owner, name)

    async def get_playlists(self, member: Member) -> list[CustomPlaylist]:
        data = await self.fetchall(
            "SELECT * FROM music_playlists WHERE user_id = $1 ORDER BY uid DESC",
            member.id
        )
        if data is None:
            return []
        return [await self._serialize(row) for row in data]

    async def edit_playlist(self, uid: int, name: str = None, closed: bool = None) -> CustomPlaylist:
        if name:
            await self.execute(
                "UPDATE music_playlists SET name = $1 WHERE uid = $2",
                name, uid
            )
        elif isinstance(closed, bool):
            await self.execute(
                "UPDATE music_playlists SET closed = $1 WHERE uid = $2",
                closed, uid
            )

        return await self.get_playlist_from_uid(uid)

    async def remove_playlist(self, uid: int) -> None:
        await self.execute(
            "DELETE FROM music_playlists WHERE uid = $1", uid
        )

    async def add_track_to_playlist(self, uid: int, track: Track) -> None:
        tracks: list[int] = ast.literal_eval(
            await self.fetchval(
                "SELECT tracks FROM music_playlists WHERE uid = $1", uid
            )
        )
        tracks.append(await self._get_track_uid(track.encoded))

        await self.execute(
            "UPDATE music_playlists SET tracks = $1 WHERE uid = $2", str(tracks), uid
        )

    async def add_listened_to_playlist(self, uid: int) -> None:
        await self.execute(
            """
            UPDATE music_playlists 
            SET listened_count = listened_count + 1 
            WHERE uid = $1
            """,
            uid
        )

    async def edit_playlist_tracks(self, uid: int, track: Track, add: bool = False) -> CustomPlaylist:
        if fetched := await self.fetchval(
                "SELECT tracks FROM music_playlists WHERE uid = $1", uid
        ):
            track_uid = await self._get_track_uid(track.encoded)
            tracks: list[int] = ast.literal_eval(fetched)

            try:
                if add:
                    tracks.append(track_uid)
                else:
                    tracks.remove(track_uid)
            except ValueError:
                return await self.get_playlist_from_uid(uid)

            else:
                await self.execute(
                    "UPDATE music_playlists SET tracks = $1 WHERE uid = $2", str(tracks), uid
                )
                return await self.get_playlist_from_uid(uid)
        else:
            raise PlaylistNotFound
