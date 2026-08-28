import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# 創建一個query的要求格式 繼承pydantic的功能去驗證甚至修正
class Query(BaseModel):
    question: str
    top_k: int = 5 #有 = 表示預設值 可以空白 否則報錯


def github_get(path: str) -> dict | list | None:
    try:
        response = httpx.get(f"https://api.github.com/users/{path}")
    except httpx.RequestError:
        print("網路連線出現問題")
        return None
    if response.status_code != 200:
        return None
    return response.json()


def get_github_user(username: str) -> dict | None:
    return github_get(username)


@app.get("/")
def home():
    return {"message":"hello"}


@app.get("/ping")
def ping():
    return {"status":"ok"}


# FastAPI預設參數型別是str 但建議都寫 因為他真的會驗證並擋下錯誤
@app.get("/hello/{name}")
def hello(name: str):
    return {"greeting":f"hello {name}"}


@app.get("/double/{number}")
def double(number: int):
    return {"result":number*2}


@app.get("/github/{username}")
def github_user(username: str):
    user = get_github_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="Github user not found")
        # 為了使狀態碼跟回傳內容兩者相符 raise用於改變狀態碼
    return {
        "name":user["name"],
        "public_repos":user["public_repos"],
        "followers":user["followers"] 
    }


@app.post("/queries")
def create_query(query: Query): # query 型別是 Pydantic model → FastAPI 從 body 讀、照 Query 規格驗證
    return {
        "received_question":query.question,
        "top_k":query.top_k,
        "answer":"真實RAG答案(未開發)"
    }