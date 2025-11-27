from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import torch

app = FastAPI(title="AI Duplicate Detection Service")

# Load models at startup
model = SentenceTransformer('all-MiniLM-L6-v2')

# Zero-shot classifier for category prediction (no training needed!)
try:
    category_classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")
    CATEGORIES = ["pothole", "garbage", "street_light", "graffiti", "flooding", "noise_complaint", "broken_infrastructure", "other"]
except Exception as e:
    print(f"Warning: Could not load category classifier: {e}")
    category_classifier = None
    CATEGORIES = []

class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    embedding: List[float]

class Candidate(BaseModel):
    id: int
    text: str

class DuplicateCheckRequest(BaseModel):
    new_report_text: str
    candidates: List[Candidate]

class DuplicateMatch(BaseModel):
    id: int
    score: float

class DuplicateCheckResponse(BaseModel):
    matches: List[DuplicateMatch]

@app.get("/")
def root():
    return {"message": "ai-duplicate service is running"}

@app.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest):
    embedding = model.encode(request.text)
    return {"embedding": embedding.tolist()}

@app.post("/check_duplicates", response_model=DuplicateCheckResponse)
def check_duplicates(request: DuplicateCheckRequest):
    if not request.candidates:
        return {"matches": []}

    # Encode new report
    new_embedding = model.encode(request.new_report_text, convert_to_tensor=True)
    
    # Encode candidates
    candidate_texts = [c.text for c in request.candidates]
    candidate_embeddings = model.encode(candidate_texts, convert_to_tensor=True)
    
    # Compute cosine similarity
    cosine_scores = util.cos_sim(new_embedding, candidate_embeddings)[0]
    
    matches = []
    for i, score in enumerate(cosine_scores):
        # Threshold can be tuned. 0.7 is a reasonable starting point for "similar topic"
        if score > 0.6: 
            matches.append(DuplicateMatch(id=request.candidates[i].id, score=float(score)))
            
    # Sort by score desc
    matches.sort(key=lambda x: x.score, reverse=True)
    
    return {"matches": matches}

class CategoryRequest(BaseModel):
    text: str

class CategoryResponse(BaseModel):
    category: str
    confidence: float
    all_scores: dict

@app.post("/predict_category", response_model=CategoryResponse)
def predict_category(request: CategoryRequest):
    if not category_classifier:
        raise HTTPException(status_code=503, detail="Category classifier not available")
    
    result = category_classifier(request.text, candidate_labels=CATEGORIES)
    
    # Return top prediction
    return {
        "category": result['labels'][0],
        "confidence": float(result['scores'][0]),
        "all_scores": {label: float(score) for label, score in zip(result['labels'], result['scores'])}
    }

class SeverityRequest(BaseModel):
    text: str

class SeverityResponse(BaseModel):
    severity: str
    confidence: float

@app.post("/predict_severity", response_model=SeverityResponse)
def predict_severity(request: SeverityRequest):
    if not category_classifier:
        # Fallback if model not loaded
        return {"severity": "medium", "confidence": 0.0}
    
    severity_labels = ["critical", "high", "medium", "low"]
    result = category_classifier(request.text, candidate_labels=severity_labels)
    
    return {
        "severity": result['labels'][0],
        "confidence": float(result['scores'][0])
    }
