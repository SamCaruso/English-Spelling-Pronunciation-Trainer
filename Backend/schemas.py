from pydantic import BaseModel, StrictStr, StrictInt, ConfigDict, Field
from typing import Optional, Literal, Union, Annotated
from enum import Enum


# --- Review ---

class ReviewStatus(str, Enum):
    REVIEW_ONLY = 'review_only'
    NO_PROGRESS = 'no_progress'
    REVIEW_LEARN = 'review_and_learn'

class ReviewResponse(BaseModel):
    status: ReviewStatus


# --- User name ---

class SetNameRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: StrictStr


# --- Phonemes covered ---

class PhonemesCoveredResponse(BaseModel):
    phoneme: StrictStr
    api_word: StrictStr
    patterns: dict[StrictStr, list[StrictStr]]


# --- Learn ---

class LearnResponse(BaseModel):
    phoneme: StrictStr
    ipa: StrictStr
    api_word: StrictStr
    patterns: dict[StrictStr, list[StrictStr]]


# --- AI Exercises ---

class ExerciseItem(BaseModel):
    ipa: StrictStr
    test_id: StrictStr
    options: Optional[list[StrictStr]] = None
    no_help_prompt: StrictStr
    help_prompt: StrictStr

class Exercise(BaseModel):
    level: StrictInt
    type: StrictStr
    instructions: StrictStr
    items: list[ExerciseItem]

class ExercisesResponse(BaseModel):
    exercises: list[Exercise]


# --- Exercise answer checking ---

class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    test_id: StrictStr
    answer: StrictStr

class AnswerCorrect(BaseModel):
    answered: Literal['correct']

class AnswerIncorrect(BaseModel):
    answered: Literal['incorrect']
    attempts_left: StrictInt

class AnswerFailed(BaseModel):
    answered: Literal['failed']
    solution: StrictStr

class AnswerFailedNoHelp(BaseModel):
    answered: Literal['failed_no_help']

AnswerResponse = Annotated[
    Union[AnswerCorrect, AnswerIncorrect, AnswerFailed, AnswerFailedNoHelp],
    Field(discriminator='answered')
]


# --- Homophones ---

class HomophResponse(BaseModel):
    homoph: StrictStr
    test_id: StrictStr
    amount: StrictInt
    sample_word: StrictStr

class HomophAnswerCorrect(BaseModel):
    answered: Literal['correct']
    attempts_left: StrictInt

class HomophAnswerDone(BaseModel):
    answered: Literal['done']

class HomophAnswerIncorrect(BaseModel):
    answered: Literal['incorrect']
    attempts_left: StrictInt

class HomophAnswerFailed(BaseModel):
    answered: Literal['failed']
    solution: list[StrictStr]

HomophAnswerResponse = Annotated[
    Union[HomophAnswerCorrect, HomophAnswerDone, HomophAnswerIncorrect, HomophAnswerFailed],
    Field(discriminator='answered')
]


# --- Save progress ---

class SaveProgress(BaseModel):
    model_config = ConfigDict(extra='forbid')
    phoneme: StrictStr

class SaveProgressResponse(BaseModel):
    status: Literal['ok']
