import asyncio
import httpx
import time

BASE_URL = "http://localhost:8000/api"

async def test_endpoint(client, endpoint, is_post=False):
    try:
        if is_post:
            res = await client.post(f"{BASE_URL}{endpoint}", json={"email": "loadtest@test.de", "password": "wrong"})
        else:
            res = await client.get(f"{BASE_URL}{endpoint}")
        return 1 if res.status_code in [200, 401, 400] else 0, 0 if res.status_code in [200, 401, 400] else 1
    except Exception:
        return 0, 1

async def worker(worker_id, duration_seconds=10):
    start_time = time.time()
    successes = 0
    errors = 0
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        while time.time() - start_time < duration_seconds:
            # 80% Get (Polling), 20% DB intensive POST
            if worker_id % 5 == 0:
                s, e = await test_endpoint(client, "/auth/login", is_post=True)
            else:
                s, e = await test_endpoint(client, "/")
                
            successes += s
            errors += e
            
            # Tiny sleep to allow context switching
            await asyncio.sleep(0.01)
            
    return successes, errors

async def main():
    print("Testing connection to localhost:8000...")
    try:
        async with httpx.AsyncClient() as c:
            await c.get(f"{BASE_URL}/")
    except Exception as e:
        print(f"Cannot reach server: {e}")
        return
        
    print("Connection OK. Starting Load Test...")
    
    NUM_WORKERS = 100
    DURATION = 10
    
    print(f"Spawning {NUM_WORKERS} concurrent connections for {DURATION} seconds...")
    start_time = time.time()
    
    tasks = [worker(i, DURATION) for i in range(NUM_WORKERS)]
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    total_success = sum(r[0] for r in results)
    total_errors = sum(r[1] for r in results)
    
    rps = (total_success + total_errors) / total_time
    
    print("\n" + "="*40)
    print("📈 LOAD TEST RESULTS 📈")
    print("="*40)
    print(f"Duration:        {total_time:.2f} seconds")
    print(f"Total Requests:  {total_success + total_errors}")
    print(f"Successful:      {total_success}")
    print(f"Errors/Timeouts: {total_errors}")
    print(f"Performance:     {rps:.2f} Req/Sec")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
