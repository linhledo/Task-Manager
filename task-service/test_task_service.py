import requests

BASE_URL = "http://127.0.0.1:5001"

# creating a task
# response = requests.post(
#     f"{BASE_URL}/tasks",
#     json={
#         "user_id": 1,
#         "description": "Finish assignment",
#         "due_date": None,
#         "priority": 3
#     }
# )

# print(response.status_code)
# print(response.text)


# Replace these with a real task ID and user ID.
task_id = 19
user_id = 1

# Test completing a task
response = requests.post(
    f"{BASE_URL}/tasks/{task_id}/complete",
    json={"user_id": user_id}
)
print("Complete:", response.status_code, response.text)

# Test reverting a task
response = requests.post(
    f"{BASE_URL}/tasks/{task_id}/revert",
    json={"user_id": user_id}
)
print("Revert:", response.status_code, response.text)

# Test deleting all completed tasks for a user.
# WARNING: This permanently deletes all of user 1's completed tasks.
# Only run this if you are happy to delete those records.
response = requests.delete(
    f"{BASE_URL}/tasks/clear-completed",
    params={"user_id": user_id}
)
print("Clear completed:", response.status_code, response.text)
