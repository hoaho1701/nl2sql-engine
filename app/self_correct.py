"""Self-correction loop: retry SQL generation with the execution error fed back to the LLM."""


def answer_question(question: str, max_retries: int = 2):
    """generate_sql -> run_sql_safe; on failure, retry with (question, bad sql, error) up to
    max_retries times. Log each attempt."""
    raise NotImplementedError
