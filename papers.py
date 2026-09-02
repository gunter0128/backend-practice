from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session


app = FastAPI()


engine = create_engine("sqlite:///papers.db") # 要連線到的資料庫的種類跟位置
Base = declarative_base() # 記錄所有表定義的地方(有繼承Base就會自動記錄)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False) # session(用來對DB做任何事情的一個視窗)的產生器


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


class PaperOut(BaseModel):
    id: int
    title: str
    year: int

    model_config = ConfigDict(from_attributes=True) # 輸出的規格有這行是因為他預設是讀 dict 不會讀物件


class DeleteOutput(BaseModel):
    id: int


@app.get("/papers", response_model= list[PaperOut])
def list_paper(db: Session = Depends(get_db)): # db 這個參數是一個session物件 透過 get_db 來產生他
    return db.query(PaperDB).all()


@app.post("/papers", response_model =PaperOut)
def create_paper(paper: Paper, db: Session = Depends(get_db)):
    new = PaperDB(title = paper.title, year = paper.year) # 還沒有 id
    db.add(new)
    db.commit()
    return new


@app.get("/papers/{paper_id}", response_model= PaperOut)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    return row


@app.delete("/papers/{paper_id}", response_model= DeleteOutput)
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    deleted_id = row.id
    db.delete(row)
    db.commit()
    return {"id": deleted_id}


@app.put("/papers/{paper_id}", response_model= PaperOut)
def update_paper(paper_id: int, paper: Paper, db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    row.title = paper.title
    row.year = paper.year
    db.commit()
    return row