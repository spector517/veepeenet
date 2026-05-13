from pydantic import BaseModel, Field

class Stats(BaseModel):
    name: str
    value: int | None = Field(default=None)

class Api(BaseModel):
    stat: list[Stats] = Field(default_factory=lambda: [])
