from fastapi import FastAPI
from database import Base, engine, SessionLocal
from models import Report
from fastapi import Depends
from sqlalchemy.orm import Session
from schemas import ReportCreate, ReportOut

app = FastAPI()

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Backend running"}

@app.post("/reports", response_model=ReportOut)
def create_report(data: ReportCreate, db: Session = Depends(get_db)):
    report = Report(**data.dict())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

@app.get("/reports")
def all_reports(db: Session = Depends(get_db)):
    return db.query(Report).all()
