from canvas import CanvasClient

client = CanvasClient()
print(f"Fetching submissions from Canvas...")
print(f"Course: {client.course_id}")
print(f"Assignment: {client.assignment_id}")
print()

submissions = client.get_submissions()
print(f"Found {len(submissions)} new submissions\n")

for i, sub in enumerate(submissions[:10], 1):
    user = sub.get("user", {})
    name = user.get("name", "Unknown")
    login = user.get("login_id", "unknown")
    sub_type = sub.get("submission_type", "none")
    url = sub.get("url", "N/A")
    
    print(f"{i}. {name} ({login})")
    print(f"   Type: {sub_type}")
    print(f"   URL: {url}")
    print()
