from pydantic import BaseModel, Field


class BookingDecisionBody(BaseModel):
    reason: str | None = Field(None, max_length=2000)

