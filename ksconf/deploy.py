# -*- coding: utf-8 -*-
"""
"""

from __future__ import absolute_import, annotations, unicode_literals

import json
from dataclasses import dataclass, field
from os import fspath
from pathlib import Path

from ksconf.app import AppManifest
from ksconf.consts import MANIFEST_HASH
from ksconf.util.file import file_hash


class AppManifestStorageError(Exception):
    pass


class AppManifestStorageInvalid(AppManifestStorageError):
    pass


@dataclass
class StoredArchiveManifest:
    """
    Stored manifest for a tarball.  Typically the manifest file lives in the
    same directory as the archive.  Details around the naming, storage, and
    clean up of these persistent manifest files are managed by the caller.
    """
    archive: Path
    size: int
    mtime: float
    hash: str
    _manifest_dict: dict = field(init=False)
    _manifest: AppManifest = field(init=False, default=None)

    @property
    def manifest(self) -> AppManifest:
        # Lazy load the full manifest details later (after size/mtime/hash have been confirmed)
        if self._manifest is None:
            if self._manifest_dict:
                try:
                    self._manifest = AppManifest.from_dict(self._manifest_dict)
                except KeyError as e:
                    raise AppManifestStorageError(f"Error loading manifest {e}")

        return self._manifest

    @classmethod
    def from_dict(cls, data: dict) -> "StoredArchiveManifest":
        o = cls(Path(data["archive"]), data["size"], data["mtime"], data["hash"])
        o._manifest_dict = data["manifest"]
        return o

    def to_dict(self):
        return {
            "archive": fspath(self.archive),
            "size": self.size,
            "mtime": self.mtime,
            "hash": self.hash,
            "manifest": self.manifest.to_dict(),
        }

    def write_json_manifest(self, manifest_file: Path):
        data = self.to_dict()
        with open(manifest_file, "w") as fp:
            json.dump(data, fp)

    @classmethod
    def read_json_manifest(cls, manifest_file: Path):
        with open(manifest_file) as fp:
            data = json.load(fp)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls,
                  archive: Path,
                  manifest: AppManifest
                  ) -> "StoredArchiveManifest":
        """
        Construct instance from a tarball.
        """
        stat = archive.stat()

        hash = file_hash(archive, MANIFEST_HASH)
        o = cls(archive, stat.st_size, stat.st_mtime, hash)
        o._manifest = manifest
        return o

    @classmethod
    def from_manifest(cls,
                      archive: Path,
                      stored_file: Path) -> "StoredArchiveManifest":
        """
        Attempt to load as stored manifest from archive & stored manifest paths.
        If the archive has changed since the manifest was stored, then an
        exception will be raised indicating the reason for invalidation.
        """
        if not stored_file:
            raise AppManifestStorageInvalid("No stored manifest found")

        try:
            stored = cls.read_json_manifest(stored_file)

            if stored.archive != archive:
                raise AppManifestStorageInvalid(f"Archive name differs: {stored.archive!r} != {archive!r}")
            stat = archive.stat()
            if stored.size != stat.st_size:
                raise AppManifestStorageInvalid(f"Archive file size differs:  {stored.size} != {stat.st_size}")
            if abs(stored.mtime - stat.st_mtime) > 0.1:
                raise AppManifestStorageInvalid(f"Archive file mtime differs: {stored.mtime} vs {stat.st_mtime}")
        except (ValueError, KeyError) as e:
            raise AppManifestStorageError(f"Unable to load stored manifest due to {e}")
        return stored


def create_manifest_from_archive(archive_file: Path,
                                 manifest_file: Path,
                                 manifest: AppManifest):
    sam = StoredArchiveManifest.from_file(archive_file, manifest)
    sam.write_json_manifest(manifest_file)
    return sam


class ManifestManager:
    @staticmethod
    def get_stored_manifest_name(archive: Path):
        c = archive.with_name(f".{archive.name}.manifest")
        return c
        '''
        if c.exists():
            return c
        return None
        '''

    def manifest_from_archive(self,
                              archive: Path,
                              read_manifest=True,
                              write_manifest=True) -> AppManifest:
        manifest = None

        if read_manifest or write_manifest:
            manifest_file = self.get_stored_manifest_name(archive)

        if read_manifest and manifest_file.exists():
            try:
                sam = StoredArchiveManifest.from_manifest(archive, manifest_file)
                manifest = sam.manifest
            except AppManifestStorageError as e:
                print(f"WARN:   loading stored manifest failed:  {e}")

        if manifest is None:
            print(f"Calculating manifest for {archive}")
            manifest = AppManifest.from_archive(archive)

            if write_manifest:
                create_manifest_from_archive(archive, manifest_file, manifest)

        return manifest
