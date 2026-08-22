from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import agent, auth, catalog, policies, watchlist

app = FastAPI()

app.include_router(auth.router)
app.include_router(watchlist.router)
app.include_router(catalog.router)
app.include_router(policies.router)
app.include_router(agent.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
