from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from src.api.routes import router

# Trigger deploy
app = FastAPI(title="Trustworthy Model Registry", version="1.0.0", root_path="/default")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Request: {request.method} {request.url}")
    print(f"DEBUG: Headers: {request.headers}")
    try:
        body = await request.body()
        if body:
            print(f"DEBUG: Body: {body.decode('utf-8')}")
    except Exception as e:
        print(f"DEBUG: Could not read body: {e}")
    
    response = await call_next(request)
    
    # Capture response body for debugging
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk
    
    print(f"DEBUG: Response Status: {response.status_code}")
    try:
        print(f"DEBUG: Response Body: {response_body.decode('utf-8')}")
    except Exception:
        print(f"DEBUG: Response Body (Binary): {len(response_body)} bytes")
        
    # Reconstruct response
    from fastapi.responses import Response
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type
    )

app.include_router(router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Lambda Handler


handler = Mangum(app)
