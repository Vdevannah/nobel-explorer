from typing import Literal

from pydantic import BaseModel, ConfigDict

from backend.schemas.explanation import ExplanationLevel


QuizAnswer = Literal["A", "B", "C", "D"]


class QuizQuestionPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int
    contribution_id: int
    level: ExplanationLevel
    question: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str


class QuizQuestionCreate(BaseModel):
    contribution_id: int
    level: ExplanationLevel
    question: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str
    correct_answer: QuizAnswer
    answer_explanation: str | None = None


class QuizQuestionUpdate(QuizQuestionCreate):
    pass


class QuizAnswerReviewResponse(BaseModel):
    question_id: int
    correct_answer: QuizAnswer
    answer_explanation: str | None
