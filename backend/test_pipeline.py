import requests
import time

API_URL = "http://localhost:8000"

def test_health():
    print("Testing /api/health...")
    res = requests.get(f"{API_URL}/api/health")
    print(res.status_code, res.json())
    assert res.status_code == 200

def test_search():
    print("\nTesting /api/search...")
    payload = {"query": "marketing agency test", "max_companies": 1}
    res = requests.post(f"{API_URL}/api/search", json=payload)
    print(res.status_code, res.json())
    assert res.status_code == 200
    
    run_id = res.json()["run_id"]
    return run_id

def test_get_run(run_id):
    print(f"\nPolling run {run_id}...")
    for _ in range(20):
        res = requests.get(f"{API_URL}/api/runs/{run_id}")
        data = res.json()
        status = data.get("status")
        print(f"Status: {status}, Discovered: {data.get('discovered_companies')}, Processed: {data.get('processed_companies')}")
        if status in ["COMPLETED", "EXHAUSTED", "FAILED", "STOPPED"]:
            print(f"Final run data: {data}")
            break
        time.sleep(2)

def test_endpoints():
    print("\nTesting pagination endpoints...")
    leads_res = requests.get(f"{API_URL}/api/leads?limit=5&offset=0")
    print("Leads (limit 5):", len(leads_res.json().get("leads", [])))
    
    runs_res = requests.get(f"{API_URL}/api/runs?limit=2&offset=0")
    print("Runs (limit 2):", len(runs_res.json().get("runs", [])))

    summary_res = requests.get(f"{API_URL}/api/summary")
    print("Summary:", summary_res.json())

if __name__ == "__main__":
    test_health()
    test_endpoints()
    run_id = test_search()
    test_get_run(run_id)
    print("\nAll tests finished successfully.")
