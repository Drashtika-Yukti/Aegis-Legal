import asyncio
import json
import os
from dotenv import load_dotenv
load_dotenv() # Load .env from project root

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

# Core Engine Imports
from core.orchestrator import run_aegis_stream
from core.vault import vault
from core.memory import memory
from core.logger import get_logger

# Supabase Auth Imports
from core.supabase_auth import supabase_auth
from core.auth import get_password_hash, verify_password, create_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends

logger = get_logger("AegisAPI")

app = FastAPI(
    title="Aegis Legal Intelligence API",
    description="Advanced RAG-based Legal AI Engine with Qdrant, Redis, and Supabase Auth.",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

from fastapi.responses import StreamingResponse, RedirectResponse

@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")

# --- AUTH DEPS ---

async def get_current_user(token: str = Depends(oauth2_scheme)):
    from jose import jwt, JWTError
    from core.config import settings
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = await supabase_auth.get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_admin_user(current_user = Depends(get_current_user)):
    """Dependency to restrict access to Admins only."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Access Denied: Admin privileges required."
        )
    return current_user

# --- SCHEMAS ---

# ... (other schemas)

# --- ADMIN ROUTES ---

@app.get("/api/v1/admin/debug")
async def admin_debug(admin = Depends(get_admin_user)):
    """Secret endpoint for testing RBAC."""
    return {
        "status": "authorized",
        "message": f"Welcome, Admin {admin['username']}. System diagnostics online.",
        "role": admin["role"]
    }

# --- AUTH ROUTES ---

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    dob: str # YYYY-MM-DD
    security_question: str
    security_answer: str

class ChatRequest(BaseModel):
    query: str
    session_id: str = "default-session"
    utility_context: Optional[str] = ""

class GenericResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None

# --- AUTH ROUTES ---

@app.post("/api/v1/auth/register")
async def register(user_in: UserCreate):
    db_user = await supabase_auth.get_user_by_username(user_in.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken.")
    
    hashed_pwd = get_password_hash(user_in.password)
    hashed_answer = get_password_hash(user_in.security_answer.lower().strip())
    
    user_data = {
        "username": user_in.username, 
        "email": user_in.email, 
        "hashed_password": hashed_pwd,
        "dob": user_in.dob,
        "security_question": user_in.security_question,
        "security_answer": hashed_answer
    }
    
    try:
        new_user = await supabase_auth.create_user(user_data)
        return {
            "status": "success", 
            "message": f"User created successfully. ID: {new_user['id']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloud Registration Error: {e}")

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Fetch User
    user = await supabase_auth.get_user_by_username(form_data.username)
    if not user:
        raise HTTPException(status_code=404, detail="Login Failed: Username not found.")
    
    # 2. Verify Password
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Login Failed: Incorrect password.")
    
    access_token = create_access_token(data={"sub": user["username"]})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user["id"],
        "role": user.get("role", "user")
    }

@app.post("/api/v1/auth/forgot-password")
async def forgot_password(
    username: str, 
    dob: str, 
    security_answer: str, 
    new_password: str
):
    """Secure password reset requiring DOB and Security Answer verification via Supabase."""
    user = await supabase_auth.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if user["dob"] != dob:
        raise HTTPException(status_code=400, detail="Verification failed: Incorrect DOB.")
    
    if not verify_password(security_answer.lower().strip(), user["security_answer"]):
        raise HTTPException(status_code=400, detail="Verification failed: Incorrect security answer.")
    
    new_hashed_pwd = get_password_hash(new_password)
    await supabase_auth.update_password(username, new_hashed_pwd)
    return {"status": "success", "message": "Verification successful. Password updated."}

# --- ENGINE ENDPOINTS (PROTECTED) ---

@app.get("/")
async def root():
    return {"status": "online", "engine": "Aegis Nexus", "version": "1.2.0"}

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest, current_user = Depends(get_current_user)):
    """Protected Chat Entry Point for all authenticated users."""
    logger.info(f"API | Chat Request | User: {current_user['username']} | Role: {current_user.get('role')}")
    
    async def event_generator():
        try:
            async for event in run_aegis_stream(
                query=request.query,
                session_id=request.session_id,
                user_id=current_user["username"],
                utility_context=request.utility_context
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"API Stream Error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/v1/ingest", response_model=GenericResponse)
async def ingest_document(
    file: UploadFile = File(...),
    admin = Depends(get_admin_user)
):
    """Admin-Only Ingest Endpoint."""
    logger.info(f"API | Ingest Request | File: {file.filename} | Admin: {admin['username']}")
    
    try:
        content = await file.read()
        result = await vault.ingest(file.filename, content, admin["username"])
        
        if result["status"] == "success":
            # 3. Sync to Supabase Cloud for Admin Audit
            await supabase_auth.log_document(
                user_id=admin.get("id", "admin"),
                filename=file.filename,
                metadata={"size": len(content), "content_type": file.content_type}
            )
            return {
                "status": "success", 
                "message": f"Legal document '{file.filename}' ingested and synced to cloud.",
                "chunks": result.get("chunks", 0)
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Ingestion failed."))
            
    except Exception as e:
        logger.error(f"API Ingest Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/history/{session_id}")
async def get_chat_history(session_id: str, current_user = Depends(get_current_user)):
    """Retrieve chat history for the authenticated user."""
    try:
        history = await memory.get_history(session_id, current_user["username"], k=20)
        return {"status": "success", "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/history/{session_id}")
async def clear_chat_history(session_id: str, current_user = Depends(get_current_user)):
    """Wipes the session history from Redis for the authenticated user."""
    try:
        await memory.set_cache(f"history:{session_id}:{current_user['username']}", json.dumps([]))
        return {"status": "success", "message": f"History for {session_id} cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/stats")
async def get_engine_stats(current_user = Depends(get_current_user)):
    """Returns engine health and vault statistics."""
    try:
        stats = {
            "vault_local_chunks": len(vault.documents),
            "qdrant_connected": vault.qdrant is not None,
            "redis_connected": memory.redis is not None,
            "current_user_role": current_user.get("role", "user")
        }
        if vault.qdrant:
            col = await vault.qdrant.get_collection("aegis_legal_docs")
            stats["qdrant_vectors"] = col.points_count
            
        return {"status": "success", "stats": stats}
    except Exception as e:
        return {"status": "partial_success", "error": str(e)}

@app.get("/api/v1/documents")
async def list_documents(current_user = Depends(get_current_user)):
    """Fetches the list of ingested documents from the cloud audit trail."""
    try:
        response = supabase_auth.supabase.table("aegis_documents").select("*").order("created_at", desc=True).limit(50).execute()
        return {"status": "success", "documents": response.data}
    except Exception as e:
        logger.error(f"List Docs Error: {e}")
        return {"status": "error", "message": str(e)}

# --- ERROR HANDLERS ---

from fastapi.responses import StreamingResponse, JSONResponse

# --- ERROR HANDLERS ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )

if __name__ == "__main__":
    import uvicorn
    # Use the port assigned by the cloud platform (like HuggingFace) or default to 7860
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
