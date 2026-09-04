from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone


SECRET_KEY = "dev-secret-change-me" # 簽章用的密鑰 之後要移到 .env / config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


app = FastAPI()
security = HTTPBearer()


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


# 根據請求帶來的 token 判斷"這個請求是誰發的"
# security 會去把 HTTP 請求中的 Authorization 這個 header
# Authorization: Bearer(scheme) eyJhbGc...(credentials)
# scheme: 這是甚麼授權方式 / credentials: 這種授權方式的實際憑證(這邊就是整個 token) 
# security 是一個 HTTPBearer 的物件 scheme 是 Bearer 才會通過
def get_current_user(creds: HTTPAuthorizationCredentials= Depends(security), db: Session = Depends(get_db)) -> "UserDB": 
    token = creds.credentials # token 一整串被拿出來
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # 用密鑰去算說 token 有沒有被竄改過或是正不正確
    except jwt.InvalidTokenError: # 任何的 jwt error
        raise HTTPException(status_code=401, detail="invalid token")
    user = db.get(UserDB, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


# 因為 bcrypt 只吃 bytes 所以 encode() 把 str 轉成 bytes
# gensalt() 給每組密碼隨機鹽 讓大家雜湊出來都不一樣(哪怕密碼一樣)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# 把輸入的密碼根據雜湊值中的鹽(完整雜湊的一部分前段)雜湊計算 看看跟 hased 是否一樣
def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# token 有三段： base64(header)  .  base64(payload)  .  signature
# token = base64(header) . base64(payload) . HMAC-SHA256( base64(header).base64(payload), 密鑰 )
# base64: 用只有安全字元的另一種寫法 避免內容被誤會為控制字元、分隔符號等等會在轉換過程中造成破壞風險的形式
# header: 這個 token 本身的資訊：用什麼演算法簽的
# payload: token 攜帶的實際資訊（一個小 dict）
def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) # 拿到 token 之後30分鐘到期
    payload = {"sub": str(user_id), "exp": expire} # token 裡面裝了甚麼資料: 誰的token & 是否過期
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


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
    note = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    author = relationship("AuthorDB", back_populates="papers")


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)


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

    model_config = ConfigDict(from_attributes=True) # 輸出的規格有這行是因為他預設是讀 dict 不會讀物件屬性裡面的值


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


class UserCreate(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer" # bear(持有) 誰有這個 token 就給過 不用額外證明


# owner_id=user.id 從驗證過的 token 來 並非客戶端的 body (自己宣稱)
@app.get("/papers", response_model= list[PaperOut])
def list_paper(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)): # db 這個參數是一個session物件 透過 get_db 來產生他
    return db.query(PaperDB).filter(PaperDB.owner_id == user.id).all()


@app.post("/papers", response_model =PaperOut)
def create_paper(paper: Paper, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    new = PaperDB(title = paper.title, year = paper.year, author_id = paper.author_id, owner_id = user.id)
    db.add(new)
    db.commit()
    return new


@app.get("/papers/{paper_id}", response_model= PaperOut)
def get_paper(paper_id: int, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    if row.owner_id != user.id:
        raise HTTPException(status_code=403, detail="not your paper") # authorization 不對
    return row


@app.delete("/papers/{paper_id}", response_model= DeleteOutput)
def delete_paper(paper_id: int, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    if row.owner_id != user.id:
        raise HTTPException(status_code=403, detail="not your paper")
    deleted_id = row.id
    db.delete(row)
    db.commit()
    return {"id": deleted_id}


@app.put("/papers/{paper_id}", response_model= PaperOut)
def update_paper(paper_id: int, paper: Paper, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(PaperDB, paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper not found")
    if row.owner_id != user.id:
            raise HTTPException(status_code=403, detail="not your paper")
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


@app.post("/register", response_model= UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.email == user.email).first() # .first()是一個終結條件 說給我第一筆符合條件的就好
    if existing:
        raise HTTPException(status_code=409, detail="email already registered")
    new = UserDB(email = user.email, hashed_password = hash_password(user.password))
    db.add(new)
    db.commit()
    return new


@app.post("/login", response_model= TokenOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid email or password")
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me", response_model=UserOut)
def me(user: UserDB = Depends(get_current_user)):
    return user