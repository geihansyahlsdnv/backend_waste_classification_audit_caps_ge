import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import statistics
from fastapi.testclient import TestClient

async def test_classification_performance(
    client: TestClient,
    test_token: str,
    test_image: bytes
):
    """Test performa endpoint klasifikasi"""
    # Parameters
    n_requests = 10  # Jumlah request
    max_latency = 2000  # Maximum latency dalam ms
    
    async def make_request():
        start_time = time.time()
        response = await asyncio.to_thread(client.post,
            "/api/classify",
            files={"file": ("test.jpg", test_image, "image/jpeg")},
            headers={"Authorization": f"Bearer {test_token}"}
        )
        end_time = time.time()
        return {
            "status_code": response.status_code,
            "latency": (end_time - start_time) * 1000  # Convert ke ms
        }
    
    # Run requests concurrently
    tasks = [make_request() for _ in range(n_requests)]
    results = await asyncio.gather(*tasks)
    
    # Analyze results
    latencies = [r["latency"] for r in results]
    success_count = sum(1 for r in results if r["status_code"] == 200)
    
    # Calculate metrics
    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    success_rate = (success_count / n_requests) * 100
    
    # Assertions
    assert success_rate >= 95, f"Success rate {success_rate}% below threshold"
    assert avg_latency <= max_latency, f"Average latency {avg_latency}ms exceeds {max_latency}ms"
    assert p95_latency <= max_latency * 1.5, f"P95 latency {p95_latency}ms too high"

async def test_database_performance(
    client: TestClient,
    test_token: str
):
    """Test performa database queries"""
    # Test history endpoint dengan pagination
    start_time = time.time()
    response = client.get(
        "/api/history?page=1&per_page=100",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    query_time = (time.time() - start_time) * 1000
    
    assert response.status_code == 200
    assert query_time <= 500, f"Query time {query_time}ms exceeds 500ms"

async def test_concurrent_users(
    client: TestClient,
    test_token: str
):
    """Test sistem dengan multiple concurrent users"""
    n_concurrent = 5  # Jumlah concurrent users
    requests_per_user = 5  # Requests per user
    
    async def user_session():
        results = []
        for _ in range(requests_per_user):
            start_time = time.time()
            response = await asyncio.to_thread(client.get,
                "/api/stats/me",
                headers={"Authorization": f"Bearer {test_token}"}
            )
            end_time = time.time()
            results.append({
                "status_code": response.status_code,
                "latency": (end_time - start_time) * 1000
            })
        return results
    
    # Run concurrent user sessions
    tasks = [user_session() for _ in range(n_concurrent)]
    all_results = await asyncio.gather(*tasks)
    
    # Flatten results
    results = [r for user_results in all_results for r in user_results]
    
    # Calculate metrics
    latencies = [r["latency"] for r in results]
    success_count = sum(1 for r in results if r["status_code"] == 200)
    
    total_requests = n_concurrent * requests_per_user
    success_rate = (success_count / total_requests) * 100
    avg_latency = statistics.mean(latencies)
    
    assert success_rate >= 95, f"Success rate {success_rate}% below threshold"
    assert avg_latency <= 1000, f"Average latency {avg_latency}ms too high"