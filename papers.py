from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session


app = FastAPI()


engine = create_engine("sqlite:///papers.db") # 要連線到的資料庫的種類跟位置
Base = declarative_base() # 記錄所有表定義的地方(有繼承Base就會自動記錄)
SessionLocal = sessionmaker(bind=engine) # session(用來對DB做任何事情的一個視窗)的產生器


# 每個請求：開 session → 交給 endpoint → endpoint 結束後回來關掉
def get_db():
    db = SessionLocal()
    try:
        yield db # 暫停 把 session 交給 endpoint
    finally:
        db.close()


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
def list_paper(db: Session = Depends(get_db)): # db 這個參數是一個session物件 透過 get_db 來產生他
    rows = db.query(PaperDB).all()
    return [{"id": p.id, "title": p.title, "year": p.year} for p in rows]


@app.post("/papers")
def create_paper(paper: Paper, db: Session = Depends(get_db)):
    new = PaperDB(title = paper.title, year = paper.year) # 還沒有 id
    db.add(new)
    db.commit()
    result = {"id": new.id, "title": new.title, "year": new.year}
    return result


@app.get("/papers/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    return {"id": row.id, "title": row.title, "year": row.year}


@app.delete("/papers/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    db.delete(row)
    db.commit()
    return {"deleted": paper_id}


@app.put("/papers/{paper_id}")
def update_paper(paper_id: int, paper: Paper, db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    row.title = paper.title
    row.year = paper.year
    db.commit()
    result = {"id": row.id, "title": row.title, "year": row.year}
    return result