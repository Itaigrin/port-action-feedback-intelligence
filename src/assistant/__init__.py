"""Deterministic Product Data Assistant.

Ten predefined questions answered with pandas over the already-classified
records. No model is called at runtime, so the assistant works with no API key,
no network and no token spend.
"""

from .questions import QUESTIONS, QUESTIONS_BY_ID, AssistantQuestion, answer

__all__ = ["QUESTIONS", "QUESTIONS_BY_ID", "AssistantQuestion", "answer"]
