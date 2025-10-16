# Step 1: Create a session and store the ID in a variable
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/v1/sessions \
-H "Content-Type: application/json" \
-d '{"user_id": "test-user", "metadata": {}}' | jq -r .session_id)

echo "---"
echo "Created session with ID: $SESSION_ID"
echo "---"

# Step 2: Send a message to the streaming endpoint using the session ID
# You should see a stream of JSON events as the response.
curl -N -X POST "http://localhost:8000/api/v1/sessions/$SESSION_ID/messages/stream" \
    -H "Content-Type: application/json" \
    -d '{"message": "This is a test message about my future career.", "sensitivity_level": "medium"}'