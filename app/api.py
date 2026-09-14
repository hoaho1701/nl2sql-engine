"""FastAPI backend exposing POST /query."""

from fastapi import FastAPI

app = FastAPI()

# TODO: CORS middleware for the frontend origin
# TODO: Pydantic request/response models
# TODO: POST /query -> self_correct.answer_question, mapping exceptions to HTTP status codes
