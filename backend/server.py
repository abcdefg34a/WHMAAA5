from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import random
import string
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import cm
import base64
import aiofiles
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create uploads directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="Abschlepp-Management API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserRole:
    ADMIN = "admin"
    AUTHORITY = "authority"
    TOWING_SERVICE = "towing_service"

class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class JobStatus:
    PENDING = "pending"
    ASSIGNED = "assigned"
    ON_SITE = "on_site"
    TOWED = "towed"
    IN_YARD = "in_yard"
    RELEASED = "released"

# Auth Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str
    name: str
    # Authority fields
    authority_name: Optional[str] = None
    department: Optional[str] = None
    # Towing service fields
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    yard_address: Optional[str] = None
    opening_hours: Optional[str] = None
    # NEW: Cost fields
    tow_cost: Optional[float] = None  # Anfahrtskosten
    daily_cost: Optional[float] = None  # Standkosten pro Tag
    # NEW: Business license (Base64)
    business_license: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    name: str
    authority_name: Optional[str] = None
    department: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    yard_address: Optional[str] = None
    opening_hours: Optional[str] = None
    service_code: Optional[str] = None
    linked_services: Optional[List[str]] = None
    created_at: str
    # NEW fields
    tow_cost: Optional[float] = None
    daily_cost: Optional[float] = None
    business_license: Optional[str] = None
    approval_status: Optional[str] = None
    rejection_reason: Optional[str] = None
    is_blocked: Optional[bool] = None
    # Employee/Dienstnummer fields
    dienstnummer: Optional[str] = None
    parent_authority_id: Optional[str] = None
    is_main_authority: Optional[bool] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UpdateCostsRequest(BaseModel):
    tow_cost: float
    daily_cost: float

class ApproveServiceRequest(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None

# Authority Employee Models
class CreateEmployeeRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class EmployeeResponse(BaseModel):
    id: str
    email: str
    name: str
    dienstnummer: str
    is_blocked: Optional[bool] = None
    created_at: str

# Admin User Management Models
class AdminUpdatePasswordRequest(BaseModel):
    new_password: str

class AdminBlockUserRequest(BaseModel):
    blocked: bool

# Job Models
class JobCreate(BaseModel):
    license_plate: str
    vin: Optional[str] = None
    tow_reason: str
    location_address: str
    location_lat: float
    location_lng: float
    photos: List[str] = []
    notes: Optional[str] = None
    assigned_service_id: Optional[str] = None

class JobUpdate(BaseModel):
    status: Optional[str] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None
    service_notes: Optional[str] = None
    # Release info
    owner_first_name: Optional[str] = None
    owner_last_name: Optional[str] = None
    owner_address: Optional[str] = None
    payment_method: Optional[str] = None
    payment_amount: Optional[float] = None

class BulkStatusUpdate(BaseModel):
    job_ids: List[str]
    status: str

class JobResponse(BaseModel):
    id: str
    job_number: str
    license_plate: str
    vin: Optional[str] = None
    tow_reason: str
    location_address: str
    location_lat: float
    location_lng: float
    photos: List[str] = []
    notes: Optional[str] = None
    status: str
    created_by_id: str
    created_by_name: str
    created_by_authority: Optional[str] = None
    created_by_dienstnummer: Optional[str] = None  # NEW: Track who created the job
    assigned_service_id: Optional[str] = None
    assigned_service_name: Optional[str] = None
    service_notes: Optional[str] = None
    service_photos: List[str] = []
    owner_first_name: Optional[str] = None
    owner_last_name: Optional[str] = None
    owner_address: Optional[str] = None
    payment_method: Optional[str] = None
    payment_amount: Optional[float] = None
    created_at: str
    updated_at: str
    on_site_at: Optional[str] = None
    towed_at: Optional[str] = None
    in_yard_at: Optional[str] = None
    released_at: Optional[str] = None

class VehicleSearchResult(BaseModel):
    found: bool
    job_number: Optional[str] = None
    license_plate: Optional[str] = None
    status: Optional[str] = None
    towed_at: Optional[str] = None
    in_yard_at: Optional[str] = None
    yard_address: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_hours: Optional[str] = None
    # NEW: Cost calculation
    tow_cost: Optional[float] = None
    daily_cost: Optional[float] = None
    days_in_yard: Optional[int] = None
    total_cost: Optional[float] = None

class LinkServiceRequest(BaseModel):
    service_code: str

class StatsResponse(BaseModel):
    total_jobs: int
    pending_jobs: int
    in_yard_jobs: int
    released_jobs: int
    total_services: int
    total_authorities: int
    pending_approvals: int

# ==================== HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def generate_service_code() -> str:
    letters = ''.join(random.choices(string.ascii_letters, k=4))
    numbers = ''.join(random.choices(string.digits, k=2))
    return letters + numbers

def generate_job_number() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TOW-{timestamp}-{random_part}"

async def generate_dienstnummer(authority_id: str) -> str:
    """Generate unique Dienstnummer for authority employees"""
    # Count existing employees for this authority
    count = await db.users.count_documents({
        "$or": [
            {"id": authority_id},
            {"parent_authority_id": authority_id}
        ],
        "dienstnummer": {"$exists": True}
    })
    # Format: DN-XXXX-NNN (DN = Dienstnummer, XXXX = first 4 chars of authority_id, NNN = sequential number)
    prefix = authority_id[:4].upper()
    return f"DN-{prefix}-{str(count + 1).zfill(3)}"

def calculate_days_in_yard(in_yard_at: str) -> int:
    """Calculate number of days a vehicle has been in the yard"""
    if not in_yard_at:
        return 0
    try:
        in_yard_date = datetime.fromisoformat(in_yard_at.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - in_yard_date
        return max(1, math.ceil(delta.total_seconds() / 86400))  # Minimum 1 day
    except:
        return 1

def calculate_total_cost(tow_cost: float, daily_cost: float, days: int) -> float:
    """Calculate total cost: tow_cost + (daily_cost * days)"""
    return (tow_cost or 0) + (daily_cost or 0) * days

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_role(roles: List[str], user: dict = Depends(get_current_user)):
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserRegister):
    # Check if email exists
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "role": data.role,
        "name": data.name,
        "created_at": now
    }
    
    if data.role == UserRole.AUTHORITY:
        user_doc["authority_name"] = data.authority_name
        user_doc["department"] = data.department
        user_doc["linked_services"] = []
        user_doc["is_main_authority"] = True
        user_doc["parent_authority_id"] = None
        # Generate Dienstnummer for main authority
        user_doc["dienstnummer"] = await generate_dienstnummer(user_id)
    elif data.role == UserRole.TOWING_SERVICE:
        # Check if business license is provided
        if not data.business_license:
            raise HTTPException(status_code=400, detail="Gewerbenachweis ist erforderlich")
        
        user_doc["company_name"] = data.company_name
        user_doc["phone"] = data.phone
        user_doc["address"] = data.address
        user_doc["yard_address"] = data.yard_address
        user_doc["opening_hours"] = data.opening_hours
        user_doc["service_code"] = generate_service_code()
        # NEW: Cost fields
        user_doc["tow_cost"] = data.tow_cost or 0
        user_doc["daily_cost"] = data.daily_cost or 0
        # NEW: Business license and approval status
        user_doc["business_license"] = data.business_license
        user_doc["approval_status"] = ApprovalStatus.PENDING
        user_doc["rejection_reason"] = None
    
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, data.role)
    user_doc.pop("password")
    user_doc.pop("_id", None)
    
    return TokenResponse(access_token=token, user=UserResponse(**user_doc))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user is blocked
    if user.get("is_blocked"):
        raise HTTPException(status_code=403, detail="Ihr Konto wurde gesperrt. Bitte kontaktieren Sie den Administrator.")
    
    # Check if towing service is approved
    if user["role"] == UserRole.TOWING_SERVICE:
        approval_status = user.get("approval_status", ApprovalStatus.PENDING)
        if approval_status == ApprovalStatus.PENDING:
            raise HTTPException(status_code=403, detail="Ihr Konto wartet noch auf Freischaltung durch einen Administrator")
        elif approval_status == ApprovalStatus.REJECTED:
            # Delete the rejected account so they can re-register
            await db.users.delete_one({"id": user["id"]})
            rejection_reason = user.get("rejection_reason", "")
            raise HTTPException(status_code=403, detail=f"Ihre Registrierung wurde abgelehnt: {rejection_reason}. Sie können sich erneut registrieren.")
    
    token = create_token(user["id"], user["role"])
    user.pop("password")
    user.pop("_id", None)
    
    return TokenResponse(access_token=token, user=UserResponse(**user))

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(**user)

# ==================== TOWING SERVICE ROUTES ====================

@api_router.get("/services", response_model=List[UserResponse])
async def get_towing_services(user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.AUTHORITY:
        # Get only linked AND approved services
        linked_ids = user.get("linked_services", [])
        if not linked_ids:
            return []
        services = await db.users.find(
            {"id": {"$in": linked_ids}, "role": UserRole.TOWING_SERVICE, "approval_status": ApprovalStatus.APPROVED},
            {"_id": 0, "password": 0}
        ).to_list(100)
    else:
        # Admin sees all approved services
        services = await db.users.find(
            {"role": UserRole.TOWING_SERVICE, "approval_status": ApprovalStatus.APPROVED},
            {"_id": 0, "password": 0}
        ).to_list(100)
    return [UserResponse(**s) for s in services]

@api_router.post("/services/link")
async def link_service(data: LinkServiceRequest, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.AUTHORITY:
        raise HTTPException(status_code=403, detail="Only authorities can link services")
    
    # Only allow linking approved services
    service = await db.users.find_one({
        "service_code": data.service_code, 
        "role": UserRole.TOWING_SERVICE,
        "approval_status": ApprovalStatus.APPROVED
    })
    if not service:
        raise HTTPException(status_code=404, detail="Kein freigeschalteter Abschleppdienst mit diesem Code gefunden")
    
    linked = user.get("linked_services", [])
    if service["id"] in linked:
        raise HTTPException(status_code=400, detail="Service already linked")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$push": {"linked_services": service["id"]}}
    )
    
    return {"message": "Service linked successfully", "service_name": service["company_name"]}

@api_router.delete("/services/unlink/{service_id}")
async def unlink_service(service_id: str, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.AUTHORITY:
        raise HTTPException(status_code=403, detail="Only authorities can unlink services")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$pull": {"linked_services": service_id}}
    )
    
    return {"message": "Service unlinked successfully"}

# NEW: Update costs endpoint for towing service
@api_router.patch("/services/costs")
async def update_costs(data: UpdateCostsRequest, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.TOWING_SERVICE:
        raise HTTPException(status_code=403, detail="Only towing services can update costs")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"tow_cost": data.tow_cost, "daily_cost": data.daily_cost}}
    )
    
    # Fetch updated user
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    return UserResponse(**updated_user)

# ==================== AUTHORITY EMPLOYEE MANAGEMENT ====================

def get_authority_id(user: dict) -> str:
    """Get the main authority ID for a user (either main authority or employee)"""
    logger.info(f"get_authority_id called with user: is_main_authority={user.get('is_main_authority')}, parent_authority_id={user.get('parent_authority_id')}, user_id={user.get('id')}")
    if user.get("is_main_authority"):
        result = user["id"]
        logger.info(f"Returning main authority ID: {result}")
        return result
    result = user.get("parent_authority_id", user["id"])
    logger.info(f"Returning parent/fallback authority ID: {result}")
    return result

@api_router.post("/authority/employees", response_model=EmployeeResponse)
async def create_employee(data: CreateEmployeeRequest, user: dict = Depends(get_current_user)):
    """Create a new employee for the authority"""
    if user["role"] != UserRole.AUTHORITY:
        raise HTTPException(status_code=403, detail="Nur Behörden können Mitarbeiter erstellen")
    
    # Only main authority can create employees
    if not user.get("is_main_authority"):
        raise HTTPException(status_code=403, detail="Nur der Haupt-Account kann Mitarbeiter erstellen")
    
    # Check if email exists
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    
    employee_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Generate Dienstnummer
    dienstnummer = await generate_dienstnummer(user["id"])
    
    employee_doc = {
        "id": employee_id,
        "email": data.email,
        "password": hash_password(data.password),
        "role": UserRole.AUTHORITY,
        "name": data.name,
        "created_at": now,
        "authority_name": user.get("authority_name"),
        "department": user.get("department"),
        "linked_services": user.get("linked_services", []),  # Inherit linked services
        "is_main_authority": False,
        "parent_authority_id": user["id"],
        "dienstnummer": dienstnummer
    }
    
    await db.users.insert_one(employee_doc)
    
    return EmployeeResponse(
        id=employee_id,
        email=data.email,
        name=data.name,
        dienstnummer=dienstnummer,
        is_blocked=False,
        created_at=now
    )

@api_router.get("/authority/employees", response_model=List[EmployeeResponse])
async def get_employees(user: dict = Depends(get_current_user)):
    """Get all employees for the authority"""
    if user["role"] != UserRole.AUTHORITY:
        raise HTTPException(status_code=403, detail="Nur Behörden")
    
    # Only main authority can view employees
    if not user.get("is_main_authority"):
        raise HTTPException(status_code=403, detail="Nur der Haupt-Account kann Mitarbeiter sehen")
    
    employees = await db.users.find(
        {"parent_authority_id": user["id"]},
        {"_id": 0, "password": 0}
    ).to_list(100)
    
    return [EmployeeResponse(
        id=e["id"],
        email=e["email"],
        name=e["name"],
        dienstnummer=e.get("dienstnummer", ""),
        is_blocked=e.get("is_blocked", False),
        created_at=e["created_at"]
    ) for e in employees]

@api_router.patch("/authority/employees/{employee_id}/block")
async def block_employee(employee_id: str, data: AdminBlockUserRequest, user: dict = Depends(get_current_user)):
    """Block/unblock an employee"""
    if user["role"] != UserRole.AUTHORITY or not user.get("is_main_authority"):
        raise HTTPException(status_code=403, detail="Nur der Haupt-Account kann Mitarbeiter sperren")
    
    employee = await db.users.find_one({"id": employee_id, "parent_authority_id": user["id"]})
    if not employee:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    
    await db.users.update_one({"id": employee_id}, {"$set": {"is_blocked": data.blocked}})
    
    action = "gesperrt" if data.blocked else "entsperrt"
    return {"message": f"Mitarbeiter {employee['name']} wurde {action}"}

@api_router.delete("/authority/employees/{employee_id}")
async def delete_employee(employee_id: str, user: dict = Depends(get_current_user)):
    """Delete an employee"""
    if user["role"] != UserRole.AUTHORITY or not user.get("is_main_authority"):
        raise HTTPException(status_code=403, detail="Nur der Haupt-Account kann Mitarbeiter löschen")
    
    employee = await db.users.find_one({"id": employee_id, "parent_authority_id": user["id"]})
    if not employee:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    
    await db.users.delete_one({"id": employee_id})
    
    return {"message": f"Mitarbeiter {employee['name']} wurde gelöscht"}

@api_router.patch("/authority/employees/{employee_id}/password")
async def update_employee_password(employee_id: str, data: AdminUpdatePasswordRequest, user: dict = Depends(get_current_user)):
    """Update an employee's password"""
    if user["role"] != UserRole.AUTHORITY or not user.get("is_main_authority"):
        raise HTTPException(status_code=403, detail="Nur der Haupt-Account kann Passwörter ändern")
    
    employee = await db.users.find_one({"id": employee_id, "parent_authority_id": user["id"]})
    if not employee:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    
    new_hashed = hash_password(data.new_password)
    await db.users.update_one({"id": employee_id}, {"$set": {"password": new_hashed}})
    
    return {"message": f"Passwort für {employee['name']} wurde aktualisiert"}

# ==================== ADMIN APPROVAL ROUTES ====================

@api_router.get("/admin/pending-services", response_model=List[UserResponse])
async def get_pending_services(user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    services = await db.users.find(
        {"role": UserRole.TOWING_SERVICE, "approval_status": ApprovalStatus.PENDING},
        {"_id": 0, "password": 0}
    ).to_list(100)
    return [UserResponse(**s) for s in services]

@api_router.post("/admin/approve-service/{service_id}")
async def approve_service(service_id: str, data: ApproveServiceRequest, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    service = await db.users.find_one({"id": service_id, "role": UserRole.TOWING_SERVICE})
    if not service:
        raise HTTPException(status_code=404, detail="Towing service not found")
    
    if data.approved:
        await db.users.update_one(
            {"id": service_id},
            {"$set": {"approval_status": ApprovalStatus.APPROVED, "rejection_reason": None}}
        )
        return {"message": f"{service['company_name']} wurde freigeschaltet"}
    else:
        await db.users.update_one(
            {"id": service_id},
            {"$set": {"approval_status": ApprovalStatus.REJECTED, "rejection_reason": data.rejection_reason}}
        )
        return {"message": f"{service['company_name']} wurde abgelehnt"}

# ==================== JOB ROUTES ====================

@api_router.post("/jobs", response_model=JobResponse)
async def create_job(data: JobCreate, user: dict = Depends(get_current_user)):
    if user["role"] not in [UserRole.AUTHORITY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only authorities can create jobs")
    
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get assigned service name if provided
    assigned_service_name = None
    if data.assigned_service_id:
        service = await db.users.find_one({"id": data.assigned_service_id})
        if service:
            assigned_service_name = service.get("company_name")
    
    # Get the authority ID (either main or from parent)
    authority_id = get_authority_id(user)
    logger.info(f"Job creation: authority_id from get_authority_id = {authority_id}")
    
    job_doc = {
        "id": job_id,
        "job_number": generate_job_number(),
        "license_plate": data.license_plate.upper(),
        "vin": data.vin.upper() if data.vin else None,
        "tow_reason": data.tow_reason,
        "location_address": data.location_address,
        "location_lat": data.location_lat,
        "location_lng": data.location_lng,
        "photos": data.photos,
        "notes": data.notes,
        "status": JobStatus.ASSIGNED if data.assigned_service_id else JobStatus.PENDING,
        "created_by_id": user["id"],
        "created_by_name": user["name"],
        "created_by_authority": user.get("authority_name"),
        "created_by_dienstnummer": user.get("dienstnummer"),  # Track Dienstnummer
        "authority_id": authority_id,  # Main authority ID for grouping
        "assigned_service_id": data.assigned_service_id,
        "assigned_service_name": assigned_service_name,
        "service_notes": None,
        "service_photos": [],
        "owner_first_name": None,
        "owner_last_name": None,
        "owner_address": None,
        "payment_method": None,
        "payment_amount": None,
        "created_at": now,
        "updated_at": now,
        "on_site_at": None,
        "towed_at": None,
        "in_yard_at": None,
        "released_at": None
    }
    
    await db.jobs.insert_one(job_doc)
    job_doc.pop("_id", None)
    
    return JobResponse(**job_doc)

@api_router.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    
    # Filter by role
    if user["role"] == UserRole.AUTHORITY:
        # Main authority sees all jobs from their authority, employees see only their own
        if user.get("is_main_authority"):
            query["authority_id"] = user["id"]
        else:
            query["created_by_id"] = user["id"]
    elif user["role"] == UserRole.TOWING_SERVICE:
        query["assigned_service_id"] = user["id"]
    
    # Filter by status
    if status:
        query["status"] = status
    
    # Filter by date range
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            # Add time to include the entire day
            date_query["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_query
    
    # Search
    if search:
        search_upper = search.upper()
        query["$or"] = [
            {"license_plate": {"$regex": search_upper, "$options": "i"}},
            {"vin": {"$regex": search_upper, "$options": "i"}},
            {"job_number": {"$regex": search_upper, "$options": "i"}}
        ]
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [JobResponse(**j) for j in jobs]

@api_router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check access for authority users
    if user["role"] == UserRole.AUTHORITY:
        authority_id = get_authority_id(user)
        if job.get("authority_id") != authority_id and job["created_by_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
    if user["role"] == UserRole.TOWING_SERVICE and job["assigned_service_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return JobResponse(**job)

@api_router.patch("/jobs/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, data: JobUpdate, user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check access for authority users
    if user["role"] == UserRole.AUTHORITY:
        authority_id = get_authority_id(user)
        if job.get("authority_id") != authority_id and job["created_by_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
    if user["role"] == UserRole.TOWING_SERVICE and job["assigned_service_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {"updated_at": now}
    
    if data.status:
        update_data["status"] = data.status
        if data.status == JobStatus.ON_SITE:
            update_data["on_site_at"] = now
        elif data.status == JobStatus.TOWED:
            update_data["towed_at"] = now
        elif data.status == JobStatus.IN_YARD:
            update_data["in_yard_at"] = now
        elif data.status == JobStatus.RELEASED:
            update_data["released_at"] = now
    
    if data.photos:
        update_data["photos"] = data.photos
    if data.notes is not None:
        update_data["notes"] = data.notes
    if data.service_notes is not None:
        update_data["service_notes"] = data.service_notes
    if data.owner_first_name is not None:
        update_data["owner_first_name"] = data.owner_first_name
    if data.owner_last_name is not None:
        update_data["owner_last_name"] = data.owner_last_name
    if data.owner_address is not None:
        update_data["owner_address"] = data.owner_address
    if data.payment_method is not None:
        update_data["payment_method"] = data.payment_method
    if data.payment_amount is not None:
        update_data["payment_amount"] = data.payment_amount
    
    await db.jobs.update_one({"id": job_id}, {"$set": update_data})
    
    updated_job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return JobResponse(**updated_job)

# ==================== BULK STATUS UPDATE ====================

@api_router.post("/jobs/bulk-update-status")
async def bulk_update_status(data: BulkStatusUpdate, user: dict = Depends(get_current_user)):
    """Bulk update status for multiple jobs at once"""
    if user["role"] != UserRole.TOWING_SERVICE:
        raise HTTPException(status_code=403, detail="Only towing services can bulk update jobs")
    
    if not data.job_ids:
        raise HTTPException(status_code=400, detail="Keine Aufträge ausgewählt")
    
    valid_statuses = [JobStatus.ON_SITE, JobStatus.TOWED, JobStatus.IN_YARD]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Ungültiger Status für Massenänderung")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Build update data based on status
    update_data = {"status": data.status, "updated_at": now}
    if data.status == JobStatus.ON_SITE:
        update_data["on_site_at"] = now
    elif data.status == JobStatus.TOWED:
        update_data["towed_at"] = now
    elif data.status == JobStatus.IN_YARD:
        update_data["in_yard_at"] = now
    
    # Only update jobs that belong to this towing service
    result = await db.jobs.update_many(
        {"id": {"$in": data.job_ids}, "assigned_service_id": user["id"]},
        {"$set": update_data}
    )
    
    return {
        "message": f"{result.modified_count} Aufträge aktualisiert",
        "updated_count": result.modified_count
    }

@api_router.post("/jobs/{job_id}/assign/{service_id}", response_model=JobResponse)
async def assign_job(job_id: str, service_id: str, user: dict = Depends(get_current_user)):
    if user["role"] not in [UserRole.AUTHORITY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only authorities can assign jobs")
    
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    service = await db.users.find_one({"id": service_id, "role": UserRole.TOWING_SERVICE})
    if not service:
        raise HTTPException(status_code=404, detail="Towing service not found")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "assigned_service_id": service_id,
            "assigned_service_name": service["company_name"],
            "status": JobStatus.ASSIGNED,
            "updated_at": now
        }}
    )
    
    updated_job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return JobResponse(**updated_job)

@api_router.post("/jobs/{job_id}/photos")
async def add_service_photo(job_id: str, photo: str = Form(...), user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.TOWING_SERVICE:
        raise HTTPException(status_code=403, detail="Only towing services can add photos")
    
    job = await db.jobs.find_one({"id": job_id})
    if not job or job["assigned_service_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await db.jobs.update_one(
        {"id": job_id},
        {"$push": {"service_photos": photo}}
    )
    
    return {"message": "Photo added"}

# ==================== PUBLIC SEARCH ====================

@api_router.get("/search/vehicle", response_model=VehicleSearchResult)
async def search_vehicle(q: str):
    search_term = q.upper().strip()
    
    job = await db.jobs.find_one({
        "$or": [
            {"license_plate": search_term},
            {"vin": search_term}
        ],
        "status": {"$in": [JobStatus.TOWED, JobStatus.IN_YARD]}
    }, {"_id": 0})
    
    if not job:
        return VehicleSearchResult(found=False)
    
    # Get towing service info
    service = None
    tow_cost = None
    daily_cost = None
    days_in_yard = 0
    total_cost = None
    
    if job.get("assigned_service_id"):
        service = await db.users.find_one({"id": job["assigned_service_id"]}, {"_id": 0, "password": 0})
        if service:
            tow_cost = service.get("tow_cost", 0)
            daily_cost = service.get("daily_cost", 0)
            
            # Calculate days in yard
            if job.get("in_yard_at"):
                days_in_yard = calculate_days_in_yard(job["in_yard_at"])
            elif job.get("towed_at"):
                days_in_yard = calculate_days_in_yard(job["towed_at"])
            
            total_cost = calculate_total_cost(tow_cost, daily_cost, days_in_yard)
    
    return VehicleSearchResult(
        found=True,
        job_number=job["job_number"],
        license_plate=job["license_plate"],
        status=job["status"],
        towed_at=job.get("towed_at"),
        in_yard_at=job.get("in_yard_at"),
        yard_address=service.get("yard_address") if service else None,
        company_name=service.get("company_name") if service else None,
        phone=service.get("phone") if service else None,
        email=service.get("email") if service else None,
        opening_hours=service.get("opening_hours") if service else None,
        tow_cost=tow_cost,
        daily_cost=daily_cost,
        days_in_yard=days_in_yard,
        total_cost=total_cost
    )

# ==================== ADMIN ROUTES ====================

@api_router.get("/admin/stats", response_model=StatsResponse)
async def get_admin_stats(user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    total_jobs = await db.jobs.count_documents({})
    pending_jobs = await db.jobs.count_documents({"status": {"$in": [JobStatus.PENDING, JobStatus.ASSIGNED, JobStatus.ON_SITE, JobStatus.TOWED]}})
    in_yard_jobs = await db.jobs.count_documents({"status": JobStatus.IN_YARD})
    released_jobs = await db.jobs.count_documents({"status": JobStatus.RELEASED})
    total_services = await db.users.count_documents({"role": UserRole.TOWING_SERVICE, "approval_status": ApprovalStatus.APPROVED})
    total_authorities = await db.users.count_documents({"role": UserRole.AUTHORITY})
    pending_approvals = await db.users.count_documents({"role": UserRole.TOWING_SERVICE, "approval_status": ApprovalStatus.PENDING})
    
    return StatsResponse(
        total_jobs=total_jobs,
        pending_jobs=pending_jobs,
        in_yard_jobs=in_yard_jobs,
        released_jobs=released_jobs,
        total_services=total_services,
        total_authorities=total_authorities,
        pending_approvals=pending_approvals
    )

@api_router.get("/admin/jobs", response_model=List[JobResponse])
async def get_all_jobs(
    status: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {}
    if status:
        query["status"] = status
    if search:
        search_upper = search.upper()
        query["$or"] = [
            {"license_plate": {"$regex": search_upper, "$options": "i"}},
            {"vin": {"$regex": search_upper, "$options": "i"}},
            {"job_number": {"$regex": search_upper, "$options": "i"}}
        ]
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [JobResponse(**j) for j in jobs]

@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

# ==================== ADMIN USER MANAGEMENT ====================

@api_router.patch("/admin/users/{user_id}/password")
async def admin_update_password(user_id: str, data: AdminUpdatePasswordRequest, user: dict = Depends(get_current_user)):
    """Admin can update any user's password"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    
    # Don't allow changing own password through this endpoint
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Eigenes Passwort bitte über Profil ändern")
    
    new_hashed = hash_password(data.new_password)
    await db.users.update_one({"id": user_id}, {"$set": {"password": new_hashed}})
    
    return {"message": f"Passwort für {target_user.get('name', target_user['email'])} wurde aktualisiert"}

@api_router.patch("/admin/users/{user_id}/block")
async def admin_block_user(user_id: str, data: AdminBlockUserRequest, user: dict = Depends(get_current_user)):
    """Admin can block/unblock users"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    
    # Don't allow blocking yourself
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Sie können sich nicht selbst sperren")
    
    # Don't allow blocking other admins
    if target_user["role"] == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Administratoren können nicht gesperrt werden")
    
    await db.users.update_one({"id": user_id}, {"$set": {"is_blocked": data.blocked}})
    
    action = "gesperrt" if data.blocked else "entsperrt"
    return {"message": f"{target_user.get('name', target_user['email'])} wurde {action}"}

@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user: dict = Depends(get_current_user)):
    """Admin can permanently delete users"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    
    # Don't allow deleting yourself
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Sie können sich nicht selbst löschen")
    
    # Don't allow deleting other admins
    if target_user["role"] == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Administratoren können nicht gelöscht werden")
    
    user_name = target_user.get('name', target_user['email'])
    
    # Delete the user
    await db.users.delete_one({"id": user_id})
    
    return {"message": f"{user_name} wurde permanent gelöscht"}

# ==================== PDF GENERATION ====================

def format_datetime(dt_str):
    """Format ISO datetime string to German format"""
    if not dt_str or dt_str == '-':
        return '-'
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    except:
        return dt_str[:19].replace('T', ' ')

@api_router.get("/jobs/{job_id}/pdf")
async def generate_pdf(job_id: str):
    """Generate PDF - public endpoint (no auth required)"""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get service info
    service = None
    if job.get("assigned_service_id"):
        service = await db.users.find_one({"id": job["assigned_service_id"]}, {"_id": 0, "password": 0})
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=20)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, spaceAfter=10, spaceBefore=15)
    normal_style = styles['Normal']
    
    story = []
    
    # Title
    story.append(Paragraph("Abschleppprotokoll", title_style))
    story.append(Paragraph(f"Auftragsnummer: {job['job_number']}", normal_style))
    story.append(Spacer(1, 20))
    
    # Vehicle Info
    story.append(Paragraph("Fahrzeugdaten", heading_style))
    vehicle_data = [
        ["Kennzeichen:", job['license_plate']],
        ["FIN:", job.get('vin') or '-'],
        ["Abschleppgrund:", job['tow_reason']],
    ]
    vehicle_table = Table(vehicle_data, colWidths=[4*cm, 12*cm])
    vehicle_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(vehicle_table)
    
    # Location
    story.append(Paragraph("Fundort", heading_style))
    location_data = [
        ["Adresse:", job['location_address']],
        ["Koordinaten:", f"{job['location_lat']}, {job['location_lng']}"],
    ]
    location_table = Table(location_data, colWidths=[4*cm, 12*cm])
    location_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(location_table)
    
    # Detailed Timeline with all steps
    story.append(Paragraph("Zeiterfassung (alle Schritte)", heading_style))
    timeline_data = [
        ["Schritt", "Datum & Uhrzeit"],
        ["1. Meldung erfasst:", format_datetime(job.get('created_at'))],
        ["2. Vor Ort angekommen:", format_datetime(job.get('on_site_at'))],
        ["3. Abgeschleppt:", format_datetime(job.get('towed_at'))],
        ["4. Im Hof eingetroffen:", format_datetime(job.get('in_yard_at'))],
        ["5. Fahrzeug abgeholt:", format_datetime(job.get('released_at'))],
    ]
    timeline_table = Table(timeline_data, colWidths=[5*cm, 11*cm])
    timeline_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(timeline_table)
    
    # Owner Info (if released)
    if job.get('owner_first_name'):
        story.append(Paragraph("Halterdaten", heading_style))
        owner_data = [
            ["Vorname:", job.get('owner_first_name', '-')],
            ["Nachname:", job.get('owner_last_name', '-')],
            ["Adresse:", job.get('owner_address', '-')],
        ]
        owner_table = Table(owner_data, colWidths=[4*cm, 12*cm])
        owner_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(owner_table)
    
    # Payment Info
    if job.get('payment_method'):
        story.append(Paragraph("Zahlungsinformationen", heading_style))
        payment_data = [
            ["Zahlungsart:", "Bar" if job['payment_method'] == 'cash' else "Karte"],
            ["Betrag:", f"{job.get('payment_amount', 0):.2f} €"],
        ]
        payment_table = Table(payment_data, colWidths=[4*cm, 12*cm])
        payment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(payment_table)
    
    # Service Info
    if service:
        story.append(Paragraph("Abschleppdienst", heading_style))
        service_data = [
            ["Unternehmen:", service.get('company_name', '-')],
            ["Telefon:", service.get('phone', '-')],
            ["Hof-Adresse:", service.get('yard_address', '-')],
        ]
        service_table = Table(service_data, colWidths=[4*cm, 12*cm])
        service_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(service_table)
    
    # Notes
    if job.get('notes') or job.get('service_notes'):
        story.append(Paragraph("Bemerkungen", heading_style))
        if job.get('notes'):
            story.append(Paragraph(f"Behörde: {job['notes']}", normal_style))
        if job.get('service_notes'):
            story.append(Paragraph(f"Abschleppdienst: {job['service_notes']}", normal_style))
    
    doc.build(story)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Abschleppprotokoll_{job['job_number']}.pdf"}
    )

# ==================== FILE UPLOAD ====================

@api_router.post("/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix if file.filename else ".jpg"
    file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    return {"file_id": file_id, "filename": f"{file_id}{file_ext}"}

@api_router.get("/uploads/{filename}")
async def get_upload(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "Abschlepp-Management API", "version": "1.0.0"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
