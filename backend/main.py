from fastapi import FastAPI # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from database import engine, Base
from routers import auth, overview, alerts, quality, audit, users, health, reports, trace, security

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RegData Engine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(overview.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(quality.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(trace.router, prefix="/api")
app.include_router(security.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "RegData Engine API is running live against AWS & Neon!"}