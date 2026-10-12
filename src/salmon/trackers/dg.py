import re

from bs4 import BeautifulSoup

from salmon import cfg
from salmon.errors import (
    RequestError,
)
from salmon.trackers.base import BaseGazelleApi, TagRules


class DGApi(BaseGazelleApi):
    """API client for DesiGaane, a Gazelle-based tracker using the same API as OPS."""

    TAG_RULES = TagRules(max_path_length=255, sixteen_bit_above_48khz="refused")

    def __init__(self):
        self.site_code = "DG"
        self.base_url = "https://desigaane.rocks"
        self.tracker_url = "https://tracker.desigaane.rocks"
        self.site_string = "DG"

        if cfg.tracker.dg:
            dg_cfg = cfg.tracker.dg
            if dg_cfg.dottorrents_dir:
                self.dot_torrents_dir = dg_cfg.dottorrents_dir
            else:
                self.dot_torrents_dir = cfg.directory.dottorrents_dir

            self.cookie = dg_cfg.session
            if dg_cfg.api_key:
                self.api_key = dg_cfg.api_key

        super().__init__()

    def parse_most_recent_torrent_and_group_id_from_group_page(self, text: str) -> tuple[int, int]:
        """Given the HTML response from a successful upload, find the most recently uploaded torrent.

        Args:
            text: The HTML response from the upload.

        Returns:
            Tuple of (torrent_id, group_id).

        Raises:
            TypeError: If no permalink ids are found.
        """
        ids: list[tuple[int, int]] = []
        soup = BeautifulSoup(text, "lxml")
        for pl in soup.find_all("a", title="Permalink"):
            href = pl.get("href", "")
            match = re.search(r"torrents.php\?id=(\d+)\&torrentid=(\d+)", str(href))
            if match:
                ids.append((int(match[2]), int(match[1])))
        if not ids:
            raise TypeError("Could not parse torrent/group id from group page: no permalink ids found")
        return max(ids)

    async def report_lossy_master(self, torrent_id: int, comment: str, source: str) -> bool:
        """Report torrent for lossy master approval.

        Uses the same 'lossyapproval' type as OPS.

        Args:
            torrent_id: The torrent ID to report.
            comment: The report comment.
            source: Media source.

        Returns:
            True if report was successful.

        Raises:
            RequestError: If the report fails.
        """
        url = self.base_url + "/reportsv2.php"
        data = {
            "auth": self.authkey,
            "torrentid": torrent_id,
            "categoryid": 1,
            "type": "lossyapproval",
            "extra": comment,
            "submit": True,
        }
        resp = await self._request("POST", url, params={"action": "takereport"}, data=data)
        if "torrents.php" in resp.url:
            return True
        raise RequestError(
            f"Failed to report torrent for lossy master: unexpected redirect to {resp.url} (status {resp.status})"
        )
