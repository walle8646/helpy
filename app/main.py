from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import create_db_and_tables
from app.routes import home, auth, profile, consultants

app = FastAPI()

# Monta static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routes
app.include_router(home.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(consultants.router)

# 🔥 Crea tabelle al startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
