#!/bin/sh
# Default to port 5000 if PORT is not set
PORT=${PORT:-5000}
echo "Starting Gunicorn on port $PORT..."
exec gunicorn licenses_server:app --bind "0.0.0.0:$PORT"
