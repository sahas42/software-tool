from fastapi import FastAPI
import uvicorn
import sys

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "FastAPI is working"}

if __name__ == "__main__":
    print("Starting test server on port 5002...")
    sys.stdout.flush()
    uvicorn.run(app, host="127.0.0.1", port=5002)
