import re
from argparse import ArgumentParser
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.utils.schemaview import SchemaView
from packaging.version import Version


def to_snake_case(name: str) -> str:
    s = re.sub(r"(?<=[a-z])(?=[A-Z])|[-_\s]+", "_", name)
    return s.strip("_").lower()


try:
    # Replace "your_package_name" with the actual "name" field from your pyproject.toml

    __version__ = version("common_access_model")
    version = Version(__version__).base_version

except PackageNotFoundError:
    __version__ = "unknown"


def main():
    model_name = next(Path("src").glob("*/schema"), None)
    if model_name:
        model_name = model_name.parent.name

    default = f"src/{model_name}/schema/{model_name}.yaml"

    parser = ArgumentParser(
        prog="gen-monolith",
        description="Flatten multifile linkml models into a single YAML file, suitable for inclusion via local file based import",
    )
    parser.add_argument(
        "-s", "--schema", default=default, type=str, help="LinkML Model to be flattened"
    )

    args = parser.parse_args()

    if args.schema != default:
        model_name = args.schema.stem

    sv = SchemaView(args.schema)

    sv.merge_imports()
    if sv.schema is not None:
        Path("project/monolith").mkdir(parents=True, exist_ok=True)
        monofile = f"project/monolith/{model_name}-{version}.yaml"
        yaml_dumper.dump(sv.schema, monofile)
        print(f"-> {monofile}")
    else:
        raise ValueError(f"Invalid Schema: {args.schema}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(e)
