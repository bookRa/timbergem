from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Routers (relative to backend package root)
from routers.sheets import router as sheets_router
from routers.symbols import router as symbols_router


app = FastAPI()


# CORS configuration (match Flask app)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Include feature routers
app.include_router(sheets_router)
app.include_router(symbols_router)


# Static files (processed uploads & assets)
app.mount("/static", StaticFiles(directory="uploads"), name="static")


