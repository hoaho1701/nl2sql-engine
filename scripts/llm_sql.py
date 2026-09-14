from openai import OpenAI
from sqlalchemy import create_engine
from schema_context import build_schema_context, DB_PATH

client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")

SYSTEM_PROMPT = """You are a SQL expert. Given a database schema and a question,
write a single SQLite SELECT query that answers the question.

Rules:
- Only output raw SQL. No markdown, no explanation, no code fences.
- Use only tables/columns that appear in the schema below.
- Follow any (NOTE: ...) hints on relationships exactly.
"""

def generate_sql(question: str, schema_context: str) -> str:
    response = client.chat.completions.create(
        model="models/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": f"Schema:\n{schema_context}\n\nQuestion: {question}"}],
        max_tokens=512,
        temperature=0,
    )
    
    return response.choices[0].message.content

if __name__ == "__main__":
    engine = create_engine(f"sqlite:///{DB_PATH}")
    context = build_schema_context(engine)
    sql_query = generate_sql("How many orders were delivered?", context)
    print(sql_query)