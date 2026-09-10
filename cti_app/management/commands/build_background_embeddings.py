import os
import chromadb

from django.conf import settings
from django.core.management.base import BaseCommand

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from cti_app.embedding_constants import VECTOR_STORE_DIR, COLLECTION_NAME, DOC_PREFIX
from cti_app.services.embeddings import get_embeddings

# Official MITRE ATT&CK information used to answer general user questions.
# Non-essential pages and boilerplate text were removed to avoid polluting the vector store.
PDF_PATH = os.path.join(
    settings.BASE_DIR,
    "background_data/ATTACK_Design_and_Philosophy_March_2020.pdf"
)


class Command(BaseCommand):
    help = "Build MITRE ATT&CK background / philosophy embeddings"

    def handle(self, *args, **options):
        self.stdout.write("Loading ATT&CK Design & Philosophy PDF...")

        # 1. Load PDF
        loader = PyPDFLoader(PDF_PATH)
        pages = loader.load()
        # print(pages)

        # 2. Split into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " "],
        )
        chunks = splitter.split_documents(pages)

        self.stdout.write(f"Split document into {len(chunks)} chunks")

        # 3. Init embeddings + Chroma (DO NOT delete collection)
        embeddings = get_embeddings()
        client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

        # 4. Embed chunks
        for i, chunk in enumerate(chunks):
            doc_id = f"mitre-attack-design-philosophy::chunk-{i:04d}"

            # Skip if already embedded
            existing = collection.get(ids=[doc_id])
            if existing["ids"]:
                continue

            if "All Rights Reserved Approved" in chunk.page_content:
                continue
            embedding_text = f"{DOC_PREFIX} {chunk.page_content.strip()}"
            vector = embeddings.embed_query(embedding_text)
            print(embedding_text)
            print("----------------------------")
            collection.add(
                ids=[doc_id],
                embeddings=[vector],
                documents=[embedding_text],
                metadatas={
                    "type": "mitre_attack_background",
                    "title": "ATT&CK Design and Philosophy",
                    "page": chunk.metadata.get("page"),
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Background embeddings complete! Total vectors: {len(collection.get()['ids'])}"
            )
        )