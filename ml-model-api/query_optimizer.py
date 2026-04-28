import re
from typing import List

class QueryOptimizer:
    """
    Optimizes SQL-like queries for performance.
    """

    def optimize(self, query: str) -> str:
        query = query.strip().lower()

        # Replace SELECT * with explicit projection hint
        query = query.replace("select *", "select indexed_fields")

        # Remove redundant whitespace
        query = re.sub(r"\s+", " ", query)

        # Optimize WHERE TRUE conditions
        query = query.replace("where true", "")

        return query

    def analyze_query(self, query: str) -> dict:
        return {
            "has_select_all": "*" in query,
            "has_where": "where" in query.lower(),
            "complexity_score": len(query.split())
        }

    def suggest_optimizations(self, query: str) -> List[str]:
        suggestions = []

        if "*" in query:
            suggestions.append("Avoid SELECT * for better performance")

        if "join" in query.lower():
            suggestions.append("Ensure indexes exist on JOIN keys")

        if "where" not in query.lower():
            suggestions.append("Add WHERE clause to reduce scan size")

        return suggestions