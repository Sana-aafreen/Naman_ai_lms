import requests
r = requests.get("http://localhost:8000/openapi.json")
data = r.json()
paths = sorted(data.get("paths", {}).keys())

# Check specific routes
main_routes = [
    "/api/ai/chat",
    "/api/login",
    "/api/courses",
    "/api/monitoring/chat",
    "/api/kpi/me",
    "/api/kpi/department",
    "/api/kpi/org",
    "/api/kpi/rate",
    "/api/profile/{user_id}",
    "/api/sops",
]

for route in main_routes:
    exists = route in paths
    print(f"  {'YES' if exists else ' NO'}  {route}")

print(f"\nTotal routes: {len(paths)}")
# Show last 10 routes to see what the latest registered routes are
print("\nLast 10 routes:")
for p in paths[-10:]:
    print(f"  {p}")
