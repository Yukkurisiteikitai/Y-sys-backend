#!/bin/bash

# Step 1: Create a thread and store the ID in a variable
# NOTE: This assumes a user with ID "test-user" already exists in the database.
THREAD_ID=$(curl -s -X POST http://localhost:8000/api/v1/threads \
-H "Content-Type: application/json" \
-d '{"user_id": "test-user", "title": "My Test Thread"}' | jq -r .thread_id)

if [ -z "$THREAD_ID" ] || [ "$THREAD_ID" == "null" ]; then
    echo "Error: Failed to create thread. Is the server running and is the user 'test-user' in the DB?"
    echo "Response:"
    curl -s -X POST http://localhost:8000/api/v1/threads -H "Content-Type: application/json" -d '{"user_id": "test-user", "title": "My Test Thread"}'
    exit 1
fi

echo "---"
echo "Created thread with ID: $THREAD_ID"
echo "---"

# Step 2: Send a message to the streaming endpoint using the thread ID
# You should see a stream of JSON events as the response.
curl -N -X POST "http://localhost:8000/api/v1/threads/$THREAD_ID/messages/stream" \
    -H "Content-Type: application/json" \
    -d '{"message": "This is a test message about my future career.", "sensitivity_level": "medium"}'
