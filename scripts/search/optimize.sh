#!/bin/bash

# Elasticsearch Index Optimization Script

ES_HOST=${1:-"http://localhost:9200"}
INDEX_NAME=${2:-"food_items"}

echo "Optimizing index: $INDEX_NAME on $ES_HOST"

# 1. Force Merge
echo "Step 1: Force merging segments..."
curl -X POST "$ES_HOST/$INDEX_NAME/_forcemerge?max_num_segments=1"

# 2. Update Refresh Interval (temporarily increase for large indexing, then back to 1s)
echo "Step 2: Resetting refresh interval..."
curl -X PUT "$ES_HOST/$INDEX_NAME/_settings" -H 'Content-Type: application/json' -d '{
  "index": {
    "refresh_interval": "1s"
  }
}'

# 3. Check Shard Health
echo "Step 3: Checking index health..."
curl -X GET "$ES_HOST/_cat/indices/$INDEX_NAME?v"

echo "Optimization complete."
