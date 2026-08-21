import importlib.metadata
import re


def to_snake_case(name: str) -> str:
    s = re.sub(r"(?<=[a-z])(?=[A-Z])|[-_\s]+", "_", name)
    return s.strip("_").lower()


try:
    # Pull the version directly from the installed package metadata
    __version__ = importlib.metadata.version("linkml-caddie")
except importlib.metadata.PackageNotFoundError:
    # Fallback if the package isn't installed during local development
    __version__ = "0.0.0"
