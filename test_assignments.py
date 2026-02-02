from canvas import CanvasClient

client = CanvasClient()
print(f"Fetching assignments from course {client.course_id}...\n")

# Get assignments
url = f"{client.base_url}/api/v1/courses/{client.course_id}/assignments"
import requests
response = requests.get(url, headers=client.headers)

if response.status_code == 200:
    assignments = response.json()
    print(f"Found {len(assignments)} assignments:\n")
    
    for i, assignment in enumerate(assignments[:15], 1):
        aid = assignment.get("id")
        name = assignment.get("name")
        points = assignment.get("points_possible")
        has_subs = assignment.get("has_submitted_submissions", False)
        
        print(f"{i}. [{aid}] {name}")
        print(f"   Points: {points}, Has submissions: {has_subs}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)
