from __future__ import annotations

import os

import psycopg


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "reference_images")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS image_embeddings (
                    id SERIAL PRIMARY KEY,
                    url TEXT NOT NULL,
                    label TEXT,
                    embedding VECTOR(512)
                );
                """
            )
            conn.commit()


def insert_embedding(url: str, label: str | None, embedding: list[float]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO image_embeddings (url, label, embedding) VALUES (%s, %s, %s::vector)",
                (url, label, "[" + ",".join(str(value) for value in embedding) + "]"),
            )
            conn.commit()
