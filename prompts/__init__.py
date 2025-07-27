"""
Prompt模板包
"""
from .question_prompts import (
    DocumentAnalysisPrompt,
    MultipleChoicePrompt,
    FillInTheBlankPrompt,
    MatchingPrompt
)

__all__ = [
    "DocumentAnalysisPrompt",
    "MultipleChoicePrompt", 
    "FillInTheBlankPrompt",
    "MatchingPrompt"
] 