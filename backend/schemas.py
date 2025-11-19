from pydantic import BaseModel

class ReportCreate(BaseModel):
    title: str
    description: str
    category: str
    latitude: float
    longitude: float

class ReportOut(ReportCreate):
    id: int
    status: str
    class Config:
        orm_mode = True
