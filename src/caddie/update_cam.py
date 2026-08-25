import logging
import re
import sys
from argparse import ArgumentParser
from pathlib import Path

import httpx
from ruyaml import YAML
from ruyaml.scanner import ScannerError

yaml = YAML()
yaml.preserve_quotes = True
# Force strict sequence formatting without extra interstitial lines
yaml.top_level_block_style_scalar = True
yaml.default_flow_style = False

from . import to_snake_case

mcp = re.compile(r"(?P<model>[A-Za-z_]*)-(?P<version>\d\.\d\.\d)")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_model_components(filename: str) -> dict:
    match = mcp.match(filename)

    if match:
        return match.groupdict()
    else:
        raise ValueError(
            f"Filename, {filename}, doesn't match the expected pattern."
            f"Expected patter: 'model_name-X.Y.Z.yaml'"
        )


class UpstreamModel:
    def __init__(
        self,
        gh_org: str,
        gh_repo: str,
        model_name: str | None = None,
        localdir: str = "upstream-models",
    ):
        self.owner = gh_org
        self.repo = gh_repo
        self.repo_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.model_name = model_name or to_snake_case(self.repo)
        self.localdir = Path(localdir)

    def list_assets(self, version: str = "latest"):
        endpoint = f"{self.repo_url}/releases/{version}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "httpx-github-client",
        }

        print(endpoint)
        response = httpx.get(endpoint, follow_redirects=True, headers=headers)
        response.raise_for_status()
        release_data = response.json()
        assets = [
            a for a in release_data.get("assets", []) if a["name"].endswith(".yaml")
        ]

        for file in assets:
            try:
                rls = extract_model_components(filename=file["name"])
                return {
                    "filename": file["name"],
                    "url": file["browser_download_url"],  # file["url"],
                    "model_name": rls["model"],
                    "version": rls["version"],
                }
            except ValueError:
                pass

    def update_release(
        self, release_details: dict, force: bool = False, local_model: str | None = None
    ):
        self.localdir.mkdir(exist_ok=True, parents=True)

        # Catch the unversioned links as well.
        mcp2 = re.compile(r"(?P<model>[A-Za-z_]*)")
        local_model_content = None
        if local_model is not None:
            local_model = Path(local_model)  # type: ignore
            try:
                local_model_content = yaml.load(local_model.open("rt"))  # type: ignore
                local_model_content["imports"] = [
                    imp
                    for imp in local_model_content["imports"]
                    if not mcp2.search(imp)
                ]

            except ScannerError as e:
                logger.error(
                    f"Unable to properly parse the model file, {local_model!s} "
                    f"{e.problem_mark}: {e.problem}"
                )
                sys.exit(1)

        upstream_model_filename = self.localdir / release_details["filename"]

        if force or not upstream_model_filename.exists():
            headers = {"User-Agent": "httpx-github-client"}
            with httpx.stream(
                "GET", release_details["url"], headers=headers, follow_redirects=True
            ) as response:
                response.raise_for_status()

                with upstream_model_filename.open("wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Model file, {upstream_model_filename}, saved.")

        if upstream_model_filename.exists():
            if local_model_content:
                local_model_content["imports"].append(
                    str(upstream_model_filename.with_suffix(""))
                )
                with local_model.open("wt") as f:  # type: ignore
                    yaml.dump(local_model_content, f)
                print(
                    "***********************************************************\n"
                    "* \n"
                    f"* {local_model} has been updated to import '{upstream_model_filename.with_suffix('')}'\n"
                    "* \n"
                    "***********************************************************\n"
                )
            else:
                symfilename = self.localdir / f"{release_details['model_name']}.yaml"
                if symfilename.exists() or symfilename.is_symlink():
                    symfilename.unlink()

                symfilename.symlink_to(upstream_model_filename.name)
                logger.info(f"{symfilename} linked and ready for use.")
                print(
                    "***********************************************************\n"
                    "* \n"
                    f"* {symfilename} linked and ready for use.\n"
                    f"* To add this to a new model, simply import '{symfilename}' to the local model's imports\n"
                    "* \n"
                    "************************************************************"
                )


def main():
    parser = ArgumentParser(
        prog="update_cam",
        description="Check github for update to the common access model.",
    )
    parser.add_argument(
        "-m",
        "--model-repo",
        default="https://github.com/include-dcc/common-access-model",
        help="Check repository's latest to see if there is a newer version to be downloaded",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default="upstream-models",
        help="Local directory where the upstream models are to be written",
    )

    parser.add_argument(
        "-l",
        "--local-model",
        default=None,
        help="Local model filename to be updated. If not provided, the tool will generate a symlink and leave updates to the model import to the user.",
    )

    args = parser.parse_args()

    gh = "https://github.com/"
    assert gh in args.model_repo

    owner, repo = args.model_repo.replace(gh, "").split("/")

    streamer = UpstreamModel(gh_org=owner, gh_repo=repo, localdir=args.directory)
    release_details = streamer.list_assets()

    assert release_details
    streamer.update_release(release_details, local_model=args.local_model)
