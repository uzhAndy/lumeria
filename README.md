# Lumeria

## Initial Setup

To parse and generate all the necessary data run the script ***init_local_data_generation.sh*** which will run the following commands:

### Load MITRE ATT&CK Data

Read MITRE ATT&CK data into the internal relational database:

```bash
python manage.py load_mitre_data_into_relational_db
```

---

### Building Embeddings and Knowledge Graph

Embeddings used for RAG consist of both the concrete data entities from the MITRE ATT&CK matrix and general official information about MITRE ATT&CK to support answering general questions.

```bash
python manage.py build_embeddings
python manage.py build_background_embeddings
python manage.py build_graph
```

---

### Database Migrations

Create and apply database migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

---


### Generate Application Data

Generate and store data in the database:

```bash
python manage.py generate_mitigation_summaries
python manage.py classify_campaign_techniques
python manage.py simplify_tech_descriptions
python manage.py generate_campaign_summaries
python manage.py generate_campaign_faqs
python manage.py generate_attack_examples
python manage.py update_campaign_groups_similarity_scores
```

Note: python manage.py classify_campaign_techniques must be run before python manage.py generate_attack_examples and python manage.py simplify_tech_descriptions before python manage.py generate_campaign_faqs

To reduce latency, storytelling prompts are cached after their first generation.
If you need to regenerate them (for example, after prompt or model changes), clear the cache by running:

```bash
rm -rf /tmp/django_cache/*
```

To warm up the cache for faster initial responses, run:

```bash
 python manage.py warm_story_cache
```
---

## Running the Project locally

1. Start the LLM Service by running the Ollama model:

   ```bash
   ollama serve
   ```

2. Start the graph store
   (change the volumes paths to fit your repo)

    ```bash
   docker run \
   --name neo4j-mitre \
   -p 7474:7474 -p 7687:7687 \
   -v $HOME/Documents/Masterarbeit/MasterthesisHS25/backend/neo4j/data:/data \
   -v $HOME/Documents/Masterarbeit/MasterthesisHS25/backend/neo4j/logs:/logs \
   -v $HOME/Documents/Masterarbeit/MasterthesisHS25/backend/neo4j/plugins:/plugins \
   -e NEO4J_AUTH=neo4j/password \
   -e NEO4J_PLUGINS='["apoc"]' \
   -e NEO4J_apoc_export_file_enabled=true \
   -e NEO4J_apoc_import_file_enabled=true \
   -e NEO4J_apoc_import_file_use__neo4j__config=true \
   -e 'NEO4J_dbms_security_procedures_unrestricted=apoc.*' \
   -e 'NEO4J_dbms_security_procedures_allowlist=apoc.*' \
   -d \
   neo4j:5
   ```
    
3. Start the backend from the backend directory:

   ```bash
   python manage.py runserver 8000
   ```

4. Start the frontend from the frontend directory:
 
   ```bash
    npm run dev
   ```
