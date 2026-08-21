import logging
import re
from argparse import ArgumentParser
from pathlib import Path

import httpx

from . import to_snake_case

mcp = re.compile(r"(?P<model>[A-Za-z_]*)-(?P<version>\d\.\d\.\d).yaml")

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

    def update_release(self, release_details: dict, force: bool = False):
        self.localdir.mkdir(exist_ok=True, parents=True)

        local_model_filename = self.localdir / release_details["filename"]

        if force or not local_model_filename.exists():
            headers = {"User-Agent": "httpx-github-client"}
            with httpx.stream(
                "GET", release_details["url"], headers=headers, follow_redirects=True
            ) as response:
                response.raise_for_status()

                with local_model_filename.open("wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Model file, {local_model_filename}, saved.")

        if local_model_filename.exists():
            symfilename = self.localdir / f"{release_details['model_name']}.yaml"
            if symfilename.exists() or symfilename.is_symlink():
                symfilename.unlink()

            symfilename.symlink_to(local_model_filename.name)
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
    args = parser.parse_args()

    gh = "https://github.com/"
    assert gh in args.model_repo

    owner, repo = args.model_repo.replace(gh, "").split("/")

    streamer = UpstreamModel(gh_org=owner, gh_repo=repo, localdir=args.directory)
    release_details = streamer.list_assets()

    assert release_details
    streamer.update_release(release_details)
