from typing import List, Dict, Any, Optional


class ElasticsearchClient:
    def __init__(self, endpoint: str, api_key: Optional[str] = None, cloud_id: Optional[str] = None):
        from elasticsearch import Elasticsearch
        if cloud_id:
            self.client = Elasticsearch(cloud_id=cloud_id, api_key=api_key)
        else:
            self.client = Elasticsearch(endpoint, api_key=api_key)

    def search_logs(self, index: str, query: Dict[str, Any], size: int = 1000) -> List[Dict[str, Any]]:
        resp = self.client.search(index=index, query=query, size=size)
        hits = resp.get('hits', {}).get('hits', [])
        return [h.get('_source', {}) for h in hits]

    def term_query(self, index: str, field: str, value: str, size: int = 1000) -> List[Dict[str, Any]]:
        q = {"term": {field: value}}
        return self.search_logs(index=index, query=q, size=size)


