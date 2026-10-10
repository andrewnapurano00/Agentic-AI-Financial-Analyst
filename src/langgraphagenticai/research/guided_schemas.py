"""Strict model contracts; model output cannot specify provider parameters."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid', strict=True)

class Step(StrictModel):
    tool: Literal['quote_profile','annual_income','news_snapshot']
    purpose: str=Field(min_length=1,max_length=200)
    @field_validator('purpose')
    @classmethod
    def plain_purpose(cls,value):
        if '://' in value or any(ord(c)<32 for c in value):
            raise ValueError('Use a short plain-language purpose without URLs.')
        return value

class Plan(StrictModel):
    steps: list[Step]=Field(min_length=1,max_length=3)
    @model_validator(mode='after')
    def unique(self):
        if len({s.tool for s in self.steps})!=len(self.steps):
            raise ValueError('Duplicate tools.')
        return self

class Fact(StrictModel):
    evidence_id: str=Field(max_length=80)
    field: str=Field(max_length=40)
    value: str | int | float
    currency: str | None
    as_of: str | None
    basis: str=Field(max_length=80)

class Answer(StrictModel):
    interpretation: str=Field(max_length=2200)
    facts: list[Fact]=Field(max_length=12)
    risks: list[str]=Field(max_length=5)
    missing_inputs: list[str]=Field(max_length=8)
