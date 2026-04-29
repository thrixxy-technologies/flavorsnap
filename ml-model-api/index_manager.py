from typing import Dict, List

class IndexManager:
    """
    Manages logical database indexes (simulation layer).
    """

    def __init__(self):
        self.indexes: Dict[str, List[str]] = {}

    def create_index(self, table: str, columns: List[str]):
        if table not in self.indexes:
            self.indexes[table] = []

        for col in columns:
            if col not in self.indexes[table]:
                self.indexes[table].append(col)

    def drop_index(self, table: str, column: str):
        if table in self.indexes and column in self.indexes[table]:
            self.indexes[table].remove(column)

    def get_indexes(self, table: str):
        return self.indexes.get(table, [])

    def optimize_indexes(self, query_fields: List[str], table: str):
        """
        Suggest missing indexes.
        """
        existing = set(self.get_indexes(table))
        return [f for f in query_fields if f not in existing]