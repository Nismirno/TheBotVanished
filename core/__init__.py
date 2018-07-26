from .config import Config

__all__ = ["Config", "__version__"]


class VersionInfo:
    def __init__(self, major, minor, patch):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __lt__(self, other):
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __repr__(self):
        return f"VersionInfo(major={self.major}, minor={self.minor}, patch={self.patch}"

    def to_json(self):
        return [self.major, self.minor, self.patch]

__version__ = "1.0.5"
version_info = VersionInfo(1, 0, 5)
