import importlib.metadata

try:
    # Pull the version directly from the installed package metadata
    __version__ = importlib.metadata.version("linkml-caddie")
except importlib.metadata.PackageNotFoundError:
    # Fallback if the package isn't installed during local development
    __version__ = "0.0.0"
