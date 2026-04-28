import psycopg2
from psycopg2 import pool
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseClusterManager:
    def __init__(self, master_dsn, replica_dsns):
        self.master_dsn = master_dsn
        self.replica_dsns = replica_dsns
        self.master_pool = None
        self.replica_pools = []
        self._initialize_pools()

    def _initialize_pools(self):
        try:
            # Master pool for writes
            self.master_pool = pool.SimpleConnectionPool(1, 20, dsn=self.master_dsn)
            logger.info("Master database connection pool initialized.")

            # Replica pools for reads
            for dsn in self.replica_dsns:
                p = pool.SimpleConnectionPool(1, 20, dsn=dsn)
                self.replica_pools.append(p)
            logger.info(f"{len(self.replica_pools)} replica database connection pools initialized.")
        except Exception as e:
            logger.error(f"Error initializing database pools: {e}")

    def get_connection(self, readonly=True):
        """Returns a connection from the appropriate pool."""
        if readonly and self.replica_pools:
            target_pool = random.choice(self.replica_pools)
            logger.info("Using replica connection for read-only operation.")
        else:
            target_pool = self.master_pool
            logger.info("Using master connection for write operation.")
        
        return target_pool.getconn()

    def put_connection(self, conn, readonly=True):
        """Returns a connection to the pool."""
        if readonly and self.replica_pools:
            # This is a bit simplified, ideally we track which pool the conn came from
            for p in self.replica_pools:
                try:
                    p.putconn(conn)
                    return
                except:
                    continue
        else:
            self.master_pool.putconn(conn)

    def failover_test(self):
        """Simulates a failover by promoting a replica to master."""
        logger.warning("Failing over... Promoting replica to master.")
        if self.replica_pools:
            new_master_pool = self.replica_pools.pop(0)
            self.master_pool = new_master_pool
            logger.info("Failover complete. New master established.")
            return True
        return False

# Example usage
if __name__ == "__main__":
    cluster = DatabaseClusterManager(
        master_dsn="dbname=flavorsnap user=flavorsnap host=postgres-rw",
        replica_dsns=["dbname=flavorsnap user=flavorsnap host=postgres-ro-1", "dbname=flavorsnap user=flavorsnap host=postgres-ro-2"]
    )
    conn = cluster.get_connection(readonly=True)
    # Perform read operations...
    cluster.put_connection(conn, readonly=True)
