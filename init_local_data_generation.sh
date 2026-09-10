#!/bin/bash

set -e

echo "Starting CTI Navigator (LOCAL DJANGO INIT)..."

# Django setup
echo "Making migrations..."
python manage.py makemigrations
echo "Applying migrations..."
python manage.py migrate

# Data loading + generation
echo "Loading MITRE ATT&CK data..."
python manage.py load_mitre_data_into_relational_db

echo "Building knowledge graph..."
python manage.py build_graph

echo "Generating application data..."
python manage.py classify_campaign_techniques
python manage.py simplify_tech_descriptions
python manage.py generate_mitigation_summaries
python manage.py generate_campaign_summaries
python manage.py generate_campaign_faqs
python manage.py generate_attack_examples
python manage.py update_campaign_groups_similarity_scores

echo "Building embeddings..."
python manage.py build_embeddings
python manage.py build_background_embeddings

echo "Warming story cache..."
python manage.py warm_story_cache || true