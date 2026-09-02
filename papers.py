from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship


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


class AuthorDB(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    papers = relationship("PaperDB", back_populates="author")


class PaperDB(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    author_id = Column(Integer, ForeignKey("authors.id"))
    note = Column(String, nullable=True) # 新增欄位測試 alembic

    author = relationship("AuthorDB", back_populates="papers")


# Base.metadata.create_all(engine) 
# 不這麼用了 因為這邊只能創建新表 對於舊表的變動無法更改 要手動重建.db檔
# 改用以下兩行指令讓 alembic 自動去管理資料庫的變動與同步
# alembic revision --autogenerate -m "描述"
# alembic upgrade head



class Paper(BaseModel):
    title: str
    year: int
    author_id: int


class Author(BaseModel):
    name: str


class AuthorOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class PaperOut(BaseModel):
    id: int
    title: str
    year: int
    author: AuthorOut | None

    model_config = ConfigDict(from_attributes=True) # 輸出的規格有這行是因為他預設是讀 dict 不會讀物件


# 多個視角 model 讓每個 endpoint 可以拿到剛好的資料
# 一個精簡版避免直接在 AuthorOutput 裡面用 list[PaperOut]造成巢狀無限迴圈
class PaperBrief(BaseModel):
    id: int
    title: str
    year: int

    model_config = ConfigDict(from_attributes=True)


class AuthorDetail(BaseModel):
    id: int
    name: str
    papers: list[PaperBrief]

    model_config = ConfigDict(from_attributes=True)


class DeleteOutput(BaseModel):
    id: int


@app.get("/papers", response_model= list[PaperOut])
def list_paper(db: Session = Depends(get_db)): # db 這個參數是一個session物件 透過 get_db 來產生他
    return db.query(PaperDB).all()


@app.post("/papers", response_model =PaperOut)
def create_paper(paper: Paper, db: Session = Depends(get_db)):
    new = PaperDB(title = paper.title, year = paper.year, author_id = paper.author_id)
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
    row.author_id = paper.author_id
    db.commit()
    return row


@app.post("/authors", response_model= AuthorOut)
def create_author(author: Author, db: Session = Depends(get_db)):
    new = AuthorDB(name = author.name)
    db.add(new)
    db.commit()
    return new


@app.get("/authors/{author_id}", response_model= AuthorDetail)
def get_author(author_id: int, db: Session = Depends(get_db)):
    row = db.get(AuthorDB, author_id)
    if not row:
        raise HTTPException(status_code=404, detail="author not found")
    return row