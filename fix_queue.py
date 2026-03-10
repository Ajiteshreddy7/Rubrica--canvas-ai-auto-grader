"""Fix stuck queue items"""
import json
from pathlib import Path


def fix_queue():
    queue_file = Path(__file__).parent / "queue.json"

    if not queue_file.exists():
        print("[FAIL] queue.json not found")
        return

    with open(queue_file, 'r', encoding='utf-8') as f:
        queue_data = json.load(f)

    print("Current queue state:")
    print(f"  Processing: {queue_data.get('processing')}")
    print(f"  Pending: {len(queue_data.get('pending', []))}")
    print(f"  Completed: {len(queue_data.get('completed', []))}")
    print(f"  Failed: {len(queue_data.get('failed', []))}")

    # If something is stuck in processing, move it to completed or back to pending
    if queue_data.get('processing'):
        item = queue_data['processing']
        print(f"\n! Found stuck item: {item['student_login']} - {item['assignment_title']}")

        # Check if grading file exists
        assignment_id = item['assignment_id']
        assignment_title = item['assignment_title']
        student_login = item['student_login']

        # Reconstruct the expected grading file path
        from assignments import get_submission_folder
        paths = get_submission_folder(assignment_id, assignment_title, student_login)
        grading_file = paths / "grading.md"

        if grading_file.exists():
            print(f"  [OK] Grading file exists at {grading_file}")
            print(f"  -> Moving to completed")

            # Read the score from the grading file
            with open(grading_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract score from YAML frontmatter
                score = 0.0
                for line in content.split('\n'):
                    if line.startswith('score:'):
                        score = float(line.split(':')[1].strip())
                        break

            item['status'] = 'completed'
            item['completed_at'] = item.get('started_at')
            item['score'] = score
            item['grading_file'] = str(grading_file)

            queue_data['completed'].append(item)
        else:
            print(f"  [FAIL] No grading file found")
            print(f"  -> Moving back to pending queue")
            queue_data['pending'].insert(0, item)  # Put back at front

        queue_data['processing'] = None
    else:
        print("\n[OK] No stuck items found")

    # Save fixed queue
    with open(queue_file, 'w', encoding='utf-8') as f:
        json.dump(queue_data, f, indent=2)

    print("\n[OK] Queue fixed!")
    print(f"  Processing: {queue_data.get('processing')}")
    print(f"  Pending: {len(queue_data.get('pending', []))}")
    print(f"  Completed: {len(queue_data.get('completed', []))}")
    print(f"  Failed: {len(queue_data.get('failed', []))}")


if __name__ == "__main__":
    fix_queue()
