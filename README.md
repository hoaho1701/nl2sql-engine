# nl2sql-engine

🚧 **Work in progress.** Self-hosted Text-to-SQL system using a RAG pattern (schema + documentation + examples retrieved per question, following the architecture used by [vanna-ai/vanna](https://github.com/vanna-ai/vanna)), built on PostgreSQL, Ollama, ChromaDB, FastAPI, and React — 100% local, $0 cost.

**Current status**: infrastructure setup (Postgres/Ollama/ChromaDB) is blocked pending a hardware migration to Apple Silicon for local LLM inference. In the meantime, the infrastructure-independent parts of the pipeline are implemented and tested:

- Raw data exploration and schema/date-column mapping for the source dataset
- Business-rule schema documentation (enum values, fan-out and nullable-FK traps discovered from the real data)
- A gold-standard evaluation set (18 question/SQL pairs) covering aggregation, joins, subqueries, and date logic
- A defense-in-depth SQL safety layer (statement validation, multi-statement rejection via `sqlparse`) — including a documented edge case where a data-modifying CTE (`WITH x AS (DELETE ... RETURNING *) SELECT * FROM x`) can't be caught by string-level checks alone
- Prompt construction and a FastAPI backend skeleton (CORS, request/response models)

27/27 unit tests passing. See [PROGRESS.md](./PROGRESS.md) for the full build log — architecture decisions, what's done, and what's next.

## Data

Built on the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (CC BY-NC-SA 4.0).

## License

Code is [MIT licensed](./LICENSE). The dataset above is not — see its own license terms.
