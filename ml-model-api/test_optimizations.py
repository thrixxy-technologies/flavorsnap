#!/usr/bin/env python3
"""
Test script for database query optimizations.
Tests the new analytics and persistence functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analytics import analytics
from persistence import (
    get_prediction_history_paginated,
    get_aggregated_metrics,
    get_model_performance_summary,
    get_popular_labels,
    create_optimized_indexes
)
from db_config import is_db_available

def test_database_connection():
    """Test database connectivity."""
    print("Testing database connection...")
    if is_db_available():
        print("✅ Database connection successful")
        return True
    else:
        print("❌ Database connection failed")
        return False

def test_analytics_queries():
    """Test the new analytics queries."""
    print("\nTesting analytics queries...")

    try:
        # Test usage stats with pagination
        usage_result = analytics.get_usage_stats(page=1, per_page=10)
        print(f"✅ Usage stats query successful - {len(usage_result['data'])} records returned")
        print(f"   Pagination: {usage_result['pagination']}")

        # Test model performance
        perf_result = analytics.get_model_performance(page=1, per_page=10)
        print(f"✅ Model performance query successful - {len(perf_result['data'])} records returned")

        # Test user engagement
        engagement = analytics.get_user_engagement(limit=5)
        print(f"✅ User engagement query successful - {len(engagement)} categories returned")

        # Test real-time activity
        activity = analytics.get_real_time_activity(limit=5)
        print(f"✅ Real-time activity query successful - {len(activity)} activities returned")

        # Test stats cards
        cards = analytics.get_stats_cards()
        print(f"✅ Stats cards query successful - {len(cards)} cards returned")

        return True

    except Exception as e:
        print(f"❌ Analytics query test failed: {e}")
        return False

def test_persistence_queries():
    """Test the new persistence query optimizations."""
    print("\nTesting persistence query optimizations...")

    try:
        # Test paginated prediction history
        history_result = get_prediction_history_paginated(page=1, per_page=10)
        print(f"✅ Paginated history query successful - {len(history_result['data'])} records returned")
        print(f"   Pagination: {history_result['pagination']}")

        # Test aggregated metrics
        metrics = get_aggregated_metrics(group_by='day')
        print(f"✅ Aggregated metrics query successful - {len(metrics)} periods returned")

        # Test model performance summary
        summary = get_model_performance_summary(days=7)
        print(f"✅ Model performance summary query successful - {len(summary)} metrics returned")

        # Test popular labels
        labels = get_popular_labels(limit=5)
        print(f"✅ Popular labels query successful - {len(labels)} labels returned")

        return True

    except Exception as e:
        print(f"❌ Persistence query test failed: {e}")
        return False

def test_index_creation():
    """Test index creation function."""
    print("\nTesting index creation...")
    try:
        create_optimized_indexes()
        print("✅ Index creation completed successfully")
        return True
    except Exception as e:
        print(f"❌ Index creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Database Query Optimizations")
    print("=" * 50)

    # Test database connection first
    if not test_database_connection():
        print("\n❌ Cannot proceed without database connection")
        return 1

    # Run all tests
    tests = [
        test_index_creation,
        test_persistence_queries,
        test_analytics_queries
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All database optimization tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())