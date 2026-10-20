"""Prometheus exporter for CloudGuard WAF per-asset statistics.

Based on the waf-stats.sh script (gist mkol5222): queries the Infinity Portal
GraphQL API and exposes getAssetStatistics for each WebApplication as metrics.
"""
import logging
import os
import time

import requests
from prometheus_client import REGISTRY, start_http_server
from prometheus_client.core import GaugeMetricFamily

GW = os.environ.get("WAF_API_GW", "https://cloudinfra-gw.portal.checkpoint.com")
CLIENT_ID = os.environ["WAF_API_KEY"]
SECRET = os.environ["WAF_API_KEY_SECRET"]
PORT = int(os.environ.get("EXPORTER_PORT", "9466"))
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "60"))
TOKEN_TTL = 25 * 60  # Infinity Portal tokens expire after 30 min

ASSETS_QUERY = """query assets { getAssets(userDefined: true) { status assets { id name assetType } } }"""
STATS_QUERY = """query AssetStatistics($id: String!) {
  getAssetStatistics(id: $id) {
    startupTime elapsedTime status readiness recommendation
    totalRequests legitimateRequests maliciousRequests criticalRequests highRequests
    uniqueSources uniqueUrls
  }
}"""

# API field -> (metric, help)
COUNTS = {
    "totalRequests": ("cpwaf_asset_requests_total", "Total requests seen by the asset"),
    "legitimateRequests": ("cpwaf_asset_legitimate_requests", "Legitimate requests"),
    "maliciousRequests": ("cpwaf_asset_malicious_requests", "Malicious requests"),
    "criticalRequests": ("cpwaf_asset_critical_requests", "Critical severity requests"),
    "highRequests": ("cpwaf_asset_high_requests", "High severity requests"),
    "uniqueSources": ("cpwaf_asset_unique_sources", "Unique source IPs"),
    "uniqueUrls": ("cpwaf_asset_unique_urls", "Unique URLs"),
    "elapsedTime": ("cpwaf_asset_learning_elapsed", "Elapsed learning time (raw API value)"),
}

log = logging.getLogger("waf-api-exporter")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class WafApiCollector:
    def __init__(self):
        self.session = requests.Session()
        self.token, self.token_ts = None, 0.0
        self.cache, self.cache_ts = [], 0.0
        self.last_ok = 0

    def _login(self):
        r = self.session.post(f"{GW}/auth/external", json={"clientId": CLIENT_ID, "accessKey": SECRET}, timeout=20)
        r.raise_for_status()
        self.token, self.token_ts = r.json()["data"]["token"], time.time()

    def _gql(self, path, query, variables=None):
        if not self.token or time.time() - self.token_ts > TOKEN_TTL:
            self._login()
        r = self.session.post(
            f"{GW}/app/waf/{path}",
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )
        if r.status_code == 401:
            self.token = None
            return self._gql(path, query, variables)
        r.raise_for_status()
        return r.json()["data"]

    def _fetch(self):
        assets = self._gql("graphql/V1", ASSETS_QUERY)["getAssets"]["assets"]
        out = []
        for a in assets:
            if a.get("assetType") != "WebApplication":
                continue
            stats = self._gql("graphql", STATS_QUERY, {"id": a["id"]})["getAssetStatistics"] or {}
            out.append((a, stats))
        return out

    def collect(self):
        if time.time() - self.cache_ts > CACHE_SECONDS:
            try:
                self.cache, self.cache_ts, self.last_ok = self._fetch(), time.time(), 1
            except Exception:  # noqa: BLE001 - exposed as cpwaf_api_up=0
                log.exception("Error querying the WAF API")
                self.last_ok = 0

        up = GaugeMetricFamily("cpwaf_api_up", "1 if the last WAF API query succeeded")
        up.add_metric([], self.last_ok)
        yield up

        labels = ["asset_id", "asset_name"]
        families = {k: GaugeMetricFamily(m, h, labels=labels) for k, (m, h) in COUNTS.items()}
        info = GaugeMetricFamily("cpwaf_asset_info", "Asset status (value is always 1)",
                                 labels=labels + ["status", "readiness", "recommendation"])
        for a, s in self.cache:
            lv = [a["id"], a["name"]]
            for k, fam in families.items():
                v = _num(s.get(k))
                if v is not None:
                    fam.add_metric(lv, v)
            info.add_metric(lv + [str(s.get("status", "")), str(s.get("readiness", "")),
                                  str(s.get("recommendation", ""))], 1)
        yield from families.values()
        yield info


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    REGISTRY.register(WafApiCollector())
    start_http_server(PORT)
    log.info("Listening on :%d/metrics (API %s)", PORT, GW)
    while True:
        time.sleep(3600)
