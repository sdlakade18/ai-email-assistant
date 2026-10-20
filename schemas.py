
from typing import Literal

from pydantic import BaseModel, Field


class EmailClassification(BaseModel):
    category: Literal[
        "Work",
        "Personal",
        "Finance",
        "Promotions",
        "Social",
        "Updates",
        "Spam",
        "Other",
    ]

    urgency: Literal["low", "medium", "high"]

    needs_reply: bool

    short_summary: str = Field(
        min_length=1,
        max_length=250,
        description="A concise summary of the email.",
    )
