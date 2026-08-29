from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Paper(BaseModel):
    title: str
    year: int


papers = {}


@app.get("/papers")
def list_paper():
    return list(papers.values())


@app.post("/papers")
def create_paper(paper: Paper):
    new_id = max(papers, default=0) + 1
    record = {"id": new_id, "title": paper.title, "year": paper.year}
    papers[new_id] = record
    return record


@app.get("/papers/{paper_id}")
def get_paper(paper_id: int):
    if paper_id not in papers:
        raise HTTPException(status_code=404, detail="paper not found")
    return papers[paper_id]


@app.delete("/papers/{paper_id}")
def delete_paper(paper_id: int):
    if paper_id not in papers:
        raise HTTPException(status_code=404, detail="paper not found")
    del papers[paper_id]
    return {"deleted": paper_id}


@app.put("/papers/{paper_id}")
def update_paper(paper_id: int, paper: Paper):
    if paper_id not in papers:
        raise HTTPException(status_code=404, detail="paper not found")
    record = {"id": paper_id, "title": paper.title, "year": paper.year}
    papers[paper_id] = record
    return record