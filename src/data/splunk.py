from typing import List, Dict, Any


class SplunkClient:
    def __init__(self, host: str, port: int, username: str, password: str, scheme: str = 'https'):
        import splunklib.client as splunk_client
        self.service = splunk_client.connect(host=host, port=port, username=username, password=password, scheme=scheme)

    def search(self, query: str, earliest: str = '-24h', latest: str = 'now') -> List[Dict[str, Any]]:
        import splunklib.results as results
        job = self.service.jobs.create(f"search {query}", earliest_time=earliest, latest_time=latest)
        while not job.is_done():
            pass
        rr = results.ResultsReader(job.results())
        out = []
        for r in rr:
            if isinstance(r, dict):
                out.append(r)
        return out






