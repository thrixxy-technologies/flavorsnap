from elasticsearch import Elasticsearch
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FoodSearchEngine:
    def __init__(self, hosts=["http://localhost:9200"]):
        self.es = Elasticsearch(hosts=hosts)
        self.index_name = "food_items"

    def search(self, query, filters=None, size=10):
        """Performs a full-text search with relevance tuning and popularity boosting."""
        start_time = time.time()
        
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["name^3", "description^2", "ingredients"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "should": [
                        {
                            "rank_feature": {
                                "field": "popularity_score",
                                "boost": 0.5
                            }
                        }
                    ]
                }
            },
            "size": size
        }

        if filters:
            search_query["query"]["bool"]["filter"] = filters

        try:
            response = self.es.search(index=self.index_name, body=search_query)
            duration = time.time() - start_time
            logger.info(f"Search for '{query}' took {duration:.4f}s. Found {response['hits']['total']['value']} hits.")
            
            # Log analytics
            self._log_analytics(query, response['hits']['total']['value'], duration)
            
            return response['hits']['hits']
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _log_analytics(self, query, hit_count, duration):
        """Logs search analytics for performance monitoring and relevance tuning."""
        analytics_entry = {
            "query": query,
            "hit_count": hit_count,
            "latency": duration,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        # In a real app, this would go to a separate index or a database
        logger.info(f"Analytics logged: {analytics_entry}")

    def optimize_index(self):
        """Performs index optimization (forcemerge)."""
        logger.info(f"Optimizing index {self.index_name}...")
        try:
            self.es.indices.forcemerge(index=self.index_name, max_num_segments=1)
            logger.info("Index optimization complete.")
            return True
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return False

if __name__ == "__main__":
    search_engine = FoodSearchEngine()
    results = search_engine.search("spicy pasta", filters=[{"term": {"category": "Italian"}}])
    for hit in results:
        print(f"Match: {hit['_source']['name']} (Score: {hit['_score']})")
        
