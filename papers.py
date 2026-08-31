from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI()


engine = create_engine("sqlite:///papers.db") # 要連線到的資料庫的種類跟位置
Base = declarative_base() # 記錄所有表定義的地方(有繼承Base就會自動記錄)
SessionLocal = sessionmaker(bind=engine) # session(用來對DB做任何事情的一個視窗)的產生器


class PaperDB(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=False)


Base.metadata.create_all(engine) # 看 Base 清單裡有哪些表 實際去資料庫裡把它們建出來


class Paper(BaseModel):
    title: str
    year: int


@app.get("/papers")
def list_paper():
    db = SessionLocal()
    rows = db.query(PaperDB).all()
    db.close()
    return [{"id": p.id, "title": p.title, "year": p.year} for p in rows]


@app.post("/papers")
def create_paper(paper: Paper):
    db = SessionLocal()
    new = PaperDB(title = paper.title, year = paper.year) # 還沒有 id
    db.add(new)
    db.commit()
    result = {"id": new.id, "title": new.title, "year": new.year}
    db.close()
    return result


@app.get("/papers/{paper_id}")
def get_paper(paper_id: int):
    db = SessionLocal()
    row = db.get(PaperDB, paper_id)
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    return {"id": row.id, "title": row.title, "year": row.year}


@app.delete("/papers/{paper_id}")
def delete_paper(paper_id: int):
    db = SessionLocal()
    row = db.get(PaperDB, paper_id)
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="paper not found")
    db.delete(row)
    db.commit()
    db.close()
    return {"deleted": paper_id}


@app.put("/papers/{paper_id}")
def update_paper(paper_id: int, paper: Paper):
    db = SessionLocal()
    row = db.get(PaperDB, paper_id)
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="paper not found")
    row.title = paper.title
    row.year = paper.year
    db.commit()
    result = {"id": row.id, "title": row.title, "year": row.year}
    db.close()
    return result