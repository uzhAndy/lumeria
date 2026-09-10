#!/bin/sh

set -e

OLLAMA_MODELS="embeddinggemma llama3.1"

echo "Starting CTI Navigator..."

# Wait for Neo4j before building backend
echo "Waiting for Neo4j..."
until nc -z neo4j 7687; do
  sleep 2
done
echo "Neo4j is ready"

# Wait for Ollama before building backend
echo "Waiting for Ollama..."
until curl -s --max-time 2 http://ollama:11434 > /dev/null; do
  sleep 2
done
echo "Ollama is ready"

# Pull and wait for required Ollama models
for MODEL in $OLLAMA_MODELS; do
  echo "Pulling Ollama model: $MODEL..."

  curl -s -X POST "http://ollama:11434/api/pull" \
       -H "Content-Type: application/json" \
       -d "{\"name\": \"$MODEL\"}" || true

  echo "Waiting until model $MODEL is ready..."
  until curl -s http://ollama:11434/api/tags | grep -q "$MODEL"; do
    echo "Model $MODEL not ready yet..."
    sleep 2
  done

  echo "Model $MODEL is ready!"
done

# check if ollama is already fully functioning
until curl -s http://ollama:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.1","messages":[{"role":"user","content":"hi"}]}' > /dev/null; do
  echo "Ollama not ready for chat..."
  sleep 2
done

# run migrations
echo "Running migrations..."
python manage.py migrate

# Start server
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000