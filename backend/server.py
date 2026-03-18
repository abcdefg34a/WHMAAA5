# ============================================================================
# ABSCHLEPPAPP - HAUPTSERVER MIT PRISMA/POSTGRESQL
# ============================================================================
# Migration von MongoDB zu Supabase PostgreSQL
# ============================================================================

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Request, BackgroundTasks, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from prisma import Prisma
from prisma.enums import UserRole, ApprovalStatus, JobStatus, JobType, VehicleCategory, PaymentMethod, PhotoType, AuditAction
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import random
import string
import re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import cm
import base64
import math
from collections import defaultdict
import time
from PIL import Image as PILImage
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import json
import boto3
from botocore.exceptions import ClientError
import pyotp
import qrcode
from qrcode.image.pure import PyPNGImage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ============================================================================
# CONFIGURATION
# ============================================================================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Prisma client
prisma = Prisma()

# AWS SES Configuration
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_SES_REGION = os.environ.get('AWS_SES_REGION', 'eu-central-1')
AWS_SES_VERIFIED_EMAIL = os.environ.get('AWS_SES_VERIFIED_EMAIL', 'info@werhatmeinautoabgeschleppt.de')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

# Create directories
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
BACKUP_DIR = ROOT_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Helper function for enum values
def safe_enum_value(enum_val, default="unknown"):
    """Safely get enum value as string"""
    if enum_val is None:
        return default
    if hasattr(enum_val, 'value'):
        return enum_val.value.lower()
    return str(enum_val).lower()

# Rate Limiting Configuration
RATE_LIMIT_WINDOW = 900  # 15 minutes
MAX_LOGIN_ATTEMPTS = 5
login_attempts: Dict[str, List[float]] = defaultdict(list)

# Image Compression Settings
MAX_IMAGE_SIZE = (1920, 1080)
JPEG_QUALITY = 75

# DSGVO Data Retention Settings
DSGVO_RETENTION_DAYS = int(os.environ.get('DSGVO_RETENTION_DAYS', 180))
INVOICE_RETENTION_YEARS = int(os.environ.get('INVOICE_RETENTION_YEARS', 10))

# Scheduler
scheduler = AsyncIOScheduler()

# FastAPI App
app = FastAPI(title="Abschlepp-Management API (PostgreSQL)")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Setup structured logging with file rotation"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=10*1024*1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    
    audit_handler = RotatingFileHandler(
        LOG_DIR / "audit.log",
        maxBytes=10*1024*1024,
        backupCount=10
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    audit_logger = logging.getLogger('audit')
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    
    return logging.getLogger(__name__), audit_logger

logger, audit_logger = setup_logging()

# ============================================================================
# EMAIL SERVICE (AWS SES)
# ============================================================================

class EmailService:
    """Service for sending emails via AWS SES"""
    
    def __init__(self):
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            self.ses_client = boto3.client(
                'ses',
                region_name=AWS_SES_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
            self.enabled = True
            logger.info("✅ AWS SES Email Service initialized")
        else:
            self.ses_client = None
            self.enabled = False
            logger.warning("⚠️ AWS SES not configured - emails will be logged only")
        
        self.sender_email = AWS_SES_VERIFIED_EMAIL
        self.frontend_url = FRONTEND_URL
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Optional[str]:
        if not self.enabled:
            logger.info(f"[EMAIL MOCK] To: {to_email}, Subject: {subject}")
            return None
        
        try:
            body = {'Html': {'Data': html_content, 'Charset': 'UTF-8'}}
            if text_content:
                body['Text'] = {'Data': text_content, 'Charset': 'UTF-8'}
            
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': body
                }
            )
            
            logger.info(f"✅ Email sent to {to_email}, MessageId: {response['MessageId']}")
            return response['MessageId']
            
        except ClientError as e:
            logger.error(f"❌ Failed to send email: {e}")
            return None
    
    def send_password_reset_email(self, to_email: str, reset_token: str, user_name: str) -> Optional[str]:
        reset_link = f"{self.frontend_url}/reset-password?token={reset_token}"
        subject = "Passwort zurücksetzen - AbschleppPortal"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #1e293b;">Passwort zurücksetzen</h1>
            <p>Hallo {user_name},</p>
            <p>Klicken Sie auf den Button, um Ihr Passwort zurückzusetzen:</p>
            <a href="{reset_link}" style="display: inline-block; padding: 12px 24px; background-color: #f97316; color: white; text-decoration: none; border-radius: 6px;">Passwort zurücksetzen</a>
            <p style="margin-top: 20px; color: #64748b; font-size: 12px;">Dieser Link ist 1 Stunde gültig.</p>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html_content)
    
    def send_account_approved_email(self, to_email: str, user_name: str, role: str) -> Optional[str]:
        role_name = "Behörde" if role == "authority" else "Abschleppdienst"
        login_url = f"{self.frontend_url}/portal"
        subject = "Ihr Konto wurde freigeschaltet - AbschleppPortal"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #16a34a;">🎉 Konto freigeschaltet!</h1>
            <p>Hallo {user_name},</p>
            <p>Ihr Konto als <strong>{role_name}</strong> wurde freigeschaltet.</p>
            <a href="{login_url}" style="display: inline-block; padding: 12px 24px; background-color: #16a34a; color: white; text-decoration: none; border-radius: 6px;">Zum Portal</a>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html_content)

email_service = EmailService()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def validate_password(password: str) -> tuple:
    if len(password) < 8:
        return False, "Passwort muss mindestens 8 Zeichen lang sein"
    if not re.search(r'[A-Z]', password):
        return False, "Passwort muss mindestens einen Großbuchstaben enthalten"
    if not re.search(r'[a-z]', password):
        return False, "Passwort muss mindestens einen Kleinbuchstaben enthalten"
    if not re.search(r'\d', password):
        return False, "Passwort muss mindestens eine Zahl enthalten"
    return True, ""

def check_rate_limit(identifier: str) -> tuple:
    current_time = time.time()
    if len(login_attempts) > 10000:
        keys_to_delete = [k for k, v in login_attempts.items() if not any(current_time - t < RATE_LIMIT_WINDOW for t in v)]
        for k in keys_to_delete:
            login_attempts.pop(k, None)
    
    login_attempts[identifier] = [t for t in login_attempts[identifier] if current_time - t < RATE_LIMIT_WINDOW]
    
    if len(login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        oldest = min(login_attempts[identifier])
        return False, int(RATE_LIMIT_WINDOW - (current_time - oldest))
    
    return True, 0

def record_login_attempt(identifier: str):
    login_attempts[identifier].append(time.time())

def clear_login_attempts(identifier: str):
    login_attempts.pop(identifier, None)

def generate_reset_token() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

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
    count = await prisma.authorityuser.count(where={'authorityId': authority_id})
    prefix = authority_id[:4].upper()
    return f"DN-{prefix}-{str(count + 1).zfill(3)}"

def calculate_days_in_yard(in_yard_at) -> int:
    if not in_yard_at:
        return 0
    try:
        if isinstance(in_yard_at, str):
            in_yard_date = datetime.fromisoformat(in_yard_at.replace('Z', '+00:00'))
        else:
            in_yard_date = in_yard_at.replace(tzinfo=timezone.utc) if in_yard_at.tzinfo is None else in_yard_at
        now = datetime.now(timezone.utc)
        delta = now - in_yard_date
        return max(1, math.ceil(delta.total_seconds() / 86400))
    except:
        return 1

def compress_image_base64(base64_data: str, max_size: tuple = MAX_IMAGE_SIZE, quality: int = JPEG_QUALITY) -> str:
    try:
        if ',' in base64_data:
            header, data = base64_data.split(',', 1)
        else:
            header = "data:image/jpeg;base64"
            data = base64_data
        
        image_data = base64.b64decode(data)
        img = PILImage.open(BytesIO(image_data))
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        compressed_data = base64.b64encode(output.read()).decode()
        return f"data:image/jpeg;base64,{compressed_data}"
    except Exception as e:
        logger.error(f"Image compression failed: {e}")
        return base64_data

# ============================================================================
# AUDIT LOGGING
# ============================================================================

async def log_audit(
    action: str,
    user_id: str = None,
    user_name: str = None,
    user_email: str = None,
    entity_type: str = None,
    entity_id: str = None,
    details: dict = None,
    ip_address: str = None
):
    """Log audit event to PostgreSQL"""
    try:
        # Map string action to enum
        action_map = {
            "LOGIN": AuditAction.LOGIN,
            "USER_LOGIN": AuditAction.LOGIN,
            "LOGIN_FAILED": AuditAction.LOGIN_FAILED,
            "LOGIN_2FA": AuditAction.LOGIN_2FA,
            "LOGOUT": AuditAction.LOGOUT,
            "REGISTER": AuditAction.REGISTER,
            "USER_REGISTERED": AuditAction.REGISTER,
            "USER_APPROVED": AuditAction.USER_APPROVED,
            "USER_REJECTED": AuditAction.USER_REJECTED,
            "USER_BLOCKED": AuditAction.USER_BLOCKED,
            "USER_UNBLOCKED": AuditAction.USER_UNBLOCKED,
            "PASSWORD_RESET": AuditAction.PASSWORD_RESET,
            "PASSWORD_CHANGED": AuditAction.PASSWORD_CHANGED,
            "2FA_ENABLED": AuditAction.TWO_FA_ENABLED,
            "2FA_DISABLED": AuditAction.TWO_FA_DISABLED,
            "JOB_CREATED": AuditAction.JOB_CREATED,
            "JOB_UPDATED": AuditAction.JOB_UPDATED,
            "JOB_STATUS_CHANGED": AuditAction.JOB_STATUS_CHANGED,
            "JOB_ASSIGNED": AuditAction.JOB_ASSIGNED,
            "JOB_ACCEPTED": AuditAction.JOB_ACCEPTED,
            "JOB_REJECTED": AuditAction.JOB_REJECTED,
            "JOB_RELEASED": AuditAction.JOB_RELEASED,
            "SERVICE_LINKED": AuditAction.SERVICE_LINKED,
            "SERVICE_UNLINKED": AuditAction.SERVICE_UNLINKED,
            "EMPLOYEE_CREATED": AuditAction.EMPLOYEE_CREATED,
            "EMPLOYEE_DELETED": AuditAction.EMPLOYEE_DELETED,
            "INVOICE_CREATED": AuditAction.INVOICE_CREATED,
            "INVOICE_PAID": AuditAction.INVOICE_PAID,
            "DSGVO_PERSONAL_DATA_CLEANUP": AuditAction.DSGVO_PERSONAL_DATA_CLEANUP,
            "STEUERRECHT_DATA_CLEANUP": AuditAction.STEUERRECHT_DATA_CLEANUP,
            "SETTINGS_UPDATED": AuditAction.SETTINGS_UPDATED,
        }
        
        audit_action = action_map.get(action, AuditAction.SETTINGS_UPDATED)
        
        # Prepare audit data
        audit_data = {
            'action': audit_action,
            'userEmail': user_email,
            'userName': user_name,
            'entityType': entity_type,
            'entityId': entity_id,
            'ipAddress': ip_address
        }
        
        # Only add userId if it's a valid string
        if user_id and isinstance(user_id, str):
            audit_data['userId'] = user_id
        
        # Handle JSON details - must be a proper JSON value for Prisma
        if details:
            audit_data['details'] = json.dumps(details)
        
        audit_entry = await prisma.auditlog.create(data=audit_data)
        
        # Log to file as backup
        audit_logger.info(json.dumps({
            'action': action,
            'user_id': user_id,
            'user_email': user_email,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'details': details
        }, ensure_ascii=False, default=str))
        
        return audit_entry
        
    except Exception as e:
        logger.error(f"❌ Audit log failed: {e}")
        return None

# ============================================================================
# AUTHENTICATION
# ============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await prisma.user.find_unique(
            where={'id': user_id},
            include={
                'authorityUser': {
                    'include': {
                        'authority': True,
                        'parentUser': True
                    }
                },
                'towingCompanyUser': {
                    'include': {
                        'towingCompany': {
                            'include': {
                                'pricing': True
                            }
                        }
                    }
                }
            }
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(user = Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_authority(user = Depends(get_current_user)):
    if user.role != UserRole.AUTHORITY_USER:
        raise HTTPException(status_code=403, detail="Authority access required")
    return user

async def require_towing_service(user = Depends(get_current_user)):
    if user.role != UserRole.TOWING_COMPANY_USER:
        raise HTTPException(status_code=403, detail="Towing service access required")
    return user

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

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
    tow_cost: Optional[float] = None
    daily_cost: Optional[float] = None
    business_license: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserLogin2FA(BaseModel):
    temp_token: str
    totp_code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class JobCreate(BaseModel):
    license_plate: Optional[str] = None
    vin: Optional[str] = None
    tow_reason: str
    location_address: str
    location_lat: float
    location_lng: float
    photos: List[str] = []
    notes: Optional[str] = None
    assigned_service_id: Optional[str] = None
    for_authority_id: Optional[str] = None
    job_type: Optional[str] = "towing"
    sicherstellung_reason: Optional[str] = None
    vehicle_category: Optional[str] = None
    ordering_authority: Optional[str] = None
    contact_attempts: Optional[bool] = None
    contact_attempts_notes: Optional[str] = None
    estimated_vehicle_value: Optional[float] = None

class JobUpdate(BaseModel):
    status: Optional[str] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None
    service_notes: Optional[str] = None
    owner_first_name: Optional[str] = None
    owner_last_name: Optional[str] = None
    owner_address: Optional[str] = None
    payment_method: Optional[str] = None
    payment_amount: Optional[float] = None
    is_empty_trip: Optional[bool] = None

class JobEditData(BaseModel):
    license_plate: Optional[str] = None
    vin: Optional[str] = None
    tow_reason: Optional[str] = None
    notes: Optional[str] = None
    location_address: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

class LinkServiceRequest(BaseModel):
    service_code: str

class CreateEmployeeRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class PricingSettingsRequest(BaseModel):
    time_based_enabled: Optional[bool] = False
    first_half_hour: Optional[float] = None
    additional_half_hour: Optional[float] = None
    tow_cost: Optional[float] = None
    daily_cost: Optional[float] = None
    processing_fee: Optional[float] = None
    empty_trip_fee: Optional[float] = None
    night_surcharge: Optional[float] = None
    weekend_surcharge: Optional[float] = None
    heavy_vehicle_surcharge: Optional[float] = None

# ============================================================================
# AUTH ROUTES
# ============================================================================

@api_router.post("/auth/register")
async def register(data: UserRegister, request: Request, background_tasks: BackgroundTasks):
    # Check if email exists
    existing = await prisma.user.find_unique(where={'email': data.email})
    if existing:
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    
    # Validate password
    is_valid, error_msg = validate_password(data.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Map role string to enum
    role_map = {
        'admin': UserRole.ADMIN,
        'authority': UserRole.AUTHORITY_USER,
        'towing_service': UserRole.TOWING_COMPANY_USER
    }
    user_role = role_map.get(data.role)
    if not user_role:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    try:
        if data.role == 'authority':
            # Create authority first
            authority = await prisma.authority.create(
                data={
                    'name': data.authority_name or data.name,
                    'department': data.department,
                    'approvalStatus': ApprovalStatus.PENDING
                }
            )
            
            # Create user
            user = await prisma.user.create(
                data={
                    'email': data.email,
                    'passwordHash': hash_password(data.password),
                    'role': user_role,
                    'name': data.name
                }
            )
            
            # Create authority user link
            dienstnummer = await generate_dienstnummer(authority.id)
            await prisma.authorityuser.create(
                data={
                    'userId': user.id,
                    'authorityId': authority.id,
                    'dienstnummer': dienstnummer,
                    'isMainAccount': True
                }
            )
            
            await log_audit("USER_REGISTERED", user.id, data.name, data.email, "authority", authority.id, {
                "role": data.role,
                "authority_name": data.authority_name
            })
            
            raise HTTPException(
                status_code=202,
                detail="Registrierung erfolgreich! Ihr Konto muss erst von einem Administrator freigeschaltet werden."
            )
            
        elif data.role == 'towing_service':
            if not data.business_license:
                raise HTTPException(status_code=400, detail="Gewerbenachweis ist erforderlich")
            
            # Create towing company
            service_code = generate_service_code()
            company = await prisma.towingcompany.create(
                data={
                    'companyName': data.company_name or data.name,
                    'phone': data.phone or '',
                    'street': data.address,
                    'yardStreet': data.yard_address,
                    'openingHours': data.opening_hours,
                    'serviceCode': service_code,
                    'approvalStatus': ApprovalStatus.PENDING
                }
            )
            
            # Create pricing
            await prisma.towingcompanypricing.create(
                data={
                    'towingCompanyId': company.id,
                    'towCost': data.tow_cost or 0,
                    'dailyCost': data.daily_cost or 0
                }
            )
            
            # Create user
            user = await prisma.user.create(
                data={
                    'email': data.email,
                    'passwordHash': hash_password(data.password),
                    'role': user_role,
                    'name': data.name
                }
            )
            
            # Create towing company user link
            await prisma.towingcompanyuser.create(
                data={
                    'userId': user.id,
                    'towingCompanyId': company.id,
                    'isAdmin': True
                }
            )
            
            await log_audit("USER_REGISTERED", user.id, data.name, data.email, "towing_company", company.id, {
                "role": data.role,
                "company_name": data.company_name
            })
            
            raise HTTPException(
                status_code=202,
                detail="Registrierung erfolgreich! Ihr Konto muss erst von einem Administrator freigeschaltet werden."
            )
        
        else:
            # Admin registration (should be rare)
            user = await prisma.user.create(
                data={
                    'email': data.email,
                    'passwordHash': hash_password(data.password),
                    'role': user_role,
                    'name': data.name
                }
            )
            
            token = create_token(user.id, data.role)
            return TokenResponse(
                access_token=token,
                user={
                    'id': user.id,
                    'email': user.email,
                    'role': data.role,
                    'name': user.name
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Registrierung fehlgeschlagen: {str(e)}")

@api_router.post("/auth/login")
async def login(data: UserLogin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{data.email}"
    
    # Check rate limit
    is_allowed, seconds_remaining = check_rate_limit(rate_limit_key)
    if not is_allowed:
        minutes = seconds_remaining // 60
        raise HTTPException(
            status_code=429,
            detail=f"Zu viele Anmeldeversuche. Bitte warten Sie {minutes} Minuten."
        )
    
    # Find user
    user = await prisma.user.find_unique(
        where={'email': data.email},
        include={
            'authorityUser': {
                'include': {
                    'authority': True
                }
            },
            'towingCompanyUser': {
                'include': {
                    'towingCompany': {
                        'include': {
                            'pricing': True
                        }
                    }
                }
            }
        }
    )
    
    if not user or not verify_password(data.password, user.passwordHash):
        record_login_attempt(rate_limit_key)
        attempts_left = MAX_LOGIN_ATTEMPTS - len(login_attempts[rate_limit_key])
        await log_audit("LOGIN_FAILED", None, None, data.email, None, None, {
            "ip_address": client_ip,
            "attempts_left": attempts_left
        }, client_ip)
        raise HTTPException(
            status_code=401,
            detail=f"Ungültige Anmeldedaten. Noch {attempts_left} Versuche übrig."
        )
    
    # Check if blocked
    if user.isBlocked:
        raise HTTPException(status_code=403, detail="Ihr Konto wurde gesperrt.")
    
    # Check approval status for authority/towing
    if user.role == UserRole.AUTHORITY_USER and user.authorityUser:
        if user.authorityUser.authority.approvalStatus != ApprovalStatus.APPROVED:
            raise HTTPException(status_code=403, detail="Ihr Konto wartet auf Freischaltung.")
    
    if user.role == UserRole.TOWING_COMPANY_USER and user.towingCompanyUser:
        if user.towingCompanyUser.towingCompany.approvalStatus != ApprovalStatus.APPROVED:
            raise HTTPException(status_code=403, detail="Ihr Konto wartet auf Freischaltung.")
    
    # Check 2FA
    if user.totpEnabled:
        temp_token = create_token(user.id, "2fa_pending")
        return {"requires_2fa": True, "temp_token": temp_token}
    
    # Clear rate limit and create token
    clear_login_attempts(rate_limit_key)
    
    # Map role back to string for frontend compatibility
    role_str_map = {
        UserRole.ADMIN: 'admin',
        UserRole.AUTHORITY_USER: 'authority',
        UserRole.TOWING_COMPANY_USER: 'towing_service'
    }
    role_str = role_str_map.get(user.role, 'unknown')
    
    token = create_token(user.id, role_str)
    
    # Update last login
    await prisma.user.update(
        where={'id': user.id},
        data={'lastLoginAt': datetime.now(timezone.utc)}
    )
    
    await log_audit("LOGIN", user.id, user.name, user.email, None, None, {
        "ip_address": client_ip
    }, client_ip)
    
    # Build user response
    user_response = {
        'id': user.id,
        'email': user.email,
        'role': role_str,
        'name': user.name,
        'totp_enabled': user.totpEnabled
    }
    
    if user.authorityUser:
        user_response['authority_name'] = user.authorityUser.authority.name
        user_response['department'] = user.authorityUser.authority.department
        user_response['dienstnummer'] = user.authorityUser.dienstnummer
        user_response['is_main_authority'] = user.authorityUser.isMainAccount
        user_response['approval_status'] = safe_enum_value(user.authorityUser.authority.approvalStatus)
    
    if user.towingCompanyUser:
        tc = user.towingCompanyUser.towingCompany
        user_response['company_name'] = tc.companyName
        user_response['phone'] = tc.phone
        user_response['address'] = tc.street
        user_response['yard_address'] = tc.yardStreet
        user_response['yard_lat'] = tc.yardLat
        user_response['yard_lng'] = tc.yardLng
        user_response['opening_hours'] = tc.openingHours
        user_response['service_code'] = tc.serviceCode
        user_response['approval_status'] = safe_enum_value(tc.approvalStatus)
        if tc.pricing:
            user_response['tow_cost'] = tc.pricing.towCost
            user_response['daily_cost'] = tc.pricing.dailyCost
            user_response['processing_fee'] = tc.pricing.processingFee
            user_response['empty_trip_fee'] = tc.pricing.emptyTripFee
            user_response['time_based_enabled'] = tc.pricing.timeBasedEnabled
            user_response['first_half_hour'] = tc.pricing.firstHalfHour
            user_response['additional_half_hour'] = tc.pricing.additionalHalfHour
    
    return TokenResponse(access_token=token, user=user_response)

@api_router.post("/auth/login/2fa")
async def login_2fa(data: UserLogin2FA, request: Request):
    try:
        payload = jwt.decode(data.temp_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if payload.get("role") != "2fa_pending":
            raise HTTPException(status_code=401, detail="Invalid 2FA token")
        
        user = await prisma.user.find_unique(where={'id': user_id})
        if not user or not user.totpSecret:
            raise HTTPException(status_code=401, detail="2FA not configured")
        
        totp = pyotp.TOTP(user.totpSecret)
        if not totp.verify(data.totp_code):
            raise HTTPException(status_code=401, detail="Ungültiger 2FA-Code")
        
        role_str_map = {
            UserRole.ADMIN: 'admin',
            UserRole.AUTHORITY_USER: 'authority',
            UserRole.TOWING_COMPANY_USER: 'towing_service'
        }
        role_str = role_str_map.get(user.role, 'unknown')
        
        token = create_token(user.id, role_str)
        
        await log_audit("LOGIN_2FA", user.id, user.name, user.email)
        
        return TokenResponse(
            access_token=token,
            user={
                'id': user.id,
                'email': user.email,
                'role': role_str,
                'name': user.name,
                'totp_enabled': True
            }
        )
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@api_router.get("/auth/me")
async def get_me(user = Depends(get_current_user)):
    role_str_map = {
        UserRole.ADMIN: 'admin',
        UserRole.AUTHORITY_USER: 'authority',
        UserRole.TOWING_COMPANY_USER: 'towing_service'
    }
    role_str = role_str_map.get(user.role, 'unknown')
    
    response = {
        'id': user.id,
        'email': user.email,
        'role': role_str,
        'name': user.name,
        'totp_enabled': user.totpEnabled,
        'created_at': user.createdAt.isoformat() if user.createdAt else None
    }
    
    if user.authorityUser:
        response['authority_name'] = user.authorityUser.authority.name
        response['department'] = user.authorityUser.authority.department
        response['dienstnummer'] = user.authorityUser.dienstnummer
        response['is_main_authority'] = user.authorityUser.isMainAccount
        response['approval_status'] = safe_enum_value(user.authorityUser.authority.approvalStatus)
    
    if user.towingCompanyUser:
        tc = user.towingCompanyUser.towingCompany
        response['company_name'] = tc.companyName
        response['phone'] = tc.phone
        response['address'] = tc.street
        response['yard_address'] = tc.yardStreet
        response['yard_lat'] = tc.yardLat
        response['yard_lng'] = tc.yardLng
        response['opening_hours'] = tc.openingHours
        response['service_code'] = tc.serviceCode
        response['approval_status'] = safe_enum_value(tc.approvalStatus)
        if tc.pricing:
            response['tow_cost'] = tc.pricing.towCost
            response['daily_cost'] = tc.pricing.dailyCost
            response['processing_fee'] = tc.pricing.processingFee
            response['empty_trip_fee'] = tc.pricing.emptyTripFee
            response['night_surcharge'] = tc.pricing.nightSurcharge
            response['weekend_surcharge'] = tc.pricing.weekendSurcharge
            response['heavy_vehicle_surcharge'] = tc.pricing.heavyVehicleSurcharge
            response['time_based_enabled'] = tc.pricing.timeBasedEnabled
            response['first_half_hour'] = tc.pricing.firstHalfHour
            response['additional_half_hour'] = tc.pricing.additionalHalfHour
    
    return response

@api_router.post("/auth/forgot-password")
async def forgot_password(data: PasswordResetRequest, background_tasks: BackgroundTasks):
    user = await prisma.user.find_unique(where={'email': data.email})
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "Falls ein Konto mit dieser E-Mail existiert, erhalten Sie einen Link zum Zurücksetzen."}
    
    # Generate reset token
    reset_token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    await prisma.passwordresettoken.create(
        data={
            'userId': user.id,
            'token': reset_token,
            'expiresAt': expires_at
        }
    )
    
    # Send email in background
    background_tasks.add_task(
        email_service.send_password_reset_email,
        to_email=user.email,
        reset_token=reset_token,
        user_name=user.name
    )
    
    return {"message": "Falls ein Konto mit dieser E-Mail existiert, erhalten Sie einen Link zum Zurücksetzen."}

@api_router.post("/auth/reset-password")
async def reset_password(data: PasswordResetConfirm):
    token_record = await prisma.passwordresettoken.find_first(
        where={
            'token': data.token,
            'usedAt': None,
            'expiresAt': {'gt': datetime.now(timezone.utc)}
        }
    )
    
    if not token_record:
        raise HTTPException(status_code=400, detail="Token ungültig oder abgelaufen")
    
    # Validate new password
    is_valid, error_msg = validate_password(data.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Update password and mark token as used
    await prisma.user.update(
        where={'id': token_record.userId},
        data={'passwordHash': hash_password(data.new_password)}
    )
    
    await prisma.passwordresettoken.update(
        where={'id': token_record.id},
        data={'usedAt': datetime.now(timezone.utc)}
    )
    
    await log_audit("PASSWORD_RESET", token_record.userId)
    
    return {"message": "Passwort erfolgreich geändert"}

# ============================================================================
# 2FA ROUTES
# ============================================================================

@api_router.post("/auth/2fa/setup")
async def setup_2fa(user = Depends(get_current_user)):
    if user.totpEnabled:
        raise HTTPException(status_code=400, detail="2FA bereits aktiviert")
    
    # Generate secret
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    
    # Generate QR code
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="AbschleppPortal"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(image_factory=PyPNGImage)
    buffer = BytesIO()
    img.save(buffer)
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Store secret temporarily
    await prisma.user.update(
        where={'id': user.id},
        data={'totpSecret': secret}
    )
    
    return {
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "secret": secret
    }

@api_router.post("/auth/2fa/verify-setup")
async def verify_2fa_setup(data: dict, user = Depends(get_current_user)):
    totp_code = data.get('totp_code')
    if not totp_code:
        raise HTTPException(status_code=400, detail="2FA-Code erforderlich")
    
    if not user.totpSecret:
        raise HTTPException(status_code=400, detail="2FA Setup nicht gestartet")
    
    totp = pyotp.TOTP(user.totpSecret)
    if not totp.verify(totp_code):
        raise HTTPException(status_code=400, detail="Ungültiger 2FA-Code")
    
    await prisma.user.update(
        where={'id': user.id},
        data={'totpEnabled': True}
    )
    
    await log_audit("2FA_ENABLED", user.id, user.name, user.email)
    
    return {"message": "2FA erfolgreich aktiviert"}

@api_router.post("/auth/2fa/disable")
async def disable_2fa(data: dict, user = Depends(get_current_user)):
    password = data.get('password')
    if not password:
        raise HTTPException(status_code=400, detail="Passwort erforderlich")
    
    if not verify_password(password, user.passwordHash):
        raise HTTPException(status_code=401, detail="Falsches Passwort")
    
    await prisma.user.update(
        where={'id': user.id},
        data={
            'totpEnabled': False,
            'totpSecret': None
        }
    )
    
    await log_audit("2FA_DISABLED", user.id, user.name, user.email)
    
    return {"message": "2FA deaktiviert"}

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@api_router.get("/admin/stats")
async def get_admin_stats(user = Depends(require_admin)):
    total_jobs = await prisma.towingjob.count()
    pending_jobs = await prisma.towingjob.count(where={'status': {'in': [JobStatus.PENDING, JobStatus.ASSIGNED, JobStatus.ON_SITE, JobStatus.TOWED]}})
    in_yard_jobs = await prisma.towingjob.count(where={'status': JobStatus.IN_YARD})
    released_jobs = await prisma.towingjob.count(where={'status': JobStatus.RELEASED})
    total_services = await prisma.towingcompany.count()
    total_authorities = await prisma.authority.count()
    pending_service_approvals = await prisma.towingcompany.count(where={'approvalStatus': ApprovalStatus.PENDING})
    pending_authority_approvals = await prisma.authority.count(where={'approvalStatus': ApprovalStatus.PENDING})
    
    return {
        "total_jobs": total_jobs,
        "pending_jobs": pending_jobs,
        "in_yard_jobs": in_yard_jobs,
        "released_jobs": released_jobs,
        "total_services": total_services,
        "total_authorities": total_authorities,
        "pending_approvals": pending_service_approvals + pending_authority_approvals
    }

@api_router.get("/admin/users")
async def get_admin_users(
    page: int = 1,
    limit: int = 50,
    role: Optional[str] = None,
    user = Depends(require_admin)
):
    skip = (page - 1) * limit
    
    where = {}
    if role:
        role_map = {
            'admin': UserRole.ADMIN,
            'authority': UserRole.AUTHORITY_USER,
            'towing_service': UserRole.TOWING_COMPANY_USER
        }
        if role in role_map:
            where['role'] = role_map[role]
    
    users = await prisma.user.find_many(
        where=where,
        include={
            'authorityUser': {'include': {'authority': True}},
            'towingCompanyUser': {'include': {'towingCompany': True}}
        },
        skip=skip,
        take=limit,
        order={'createdAt': 'desc'}
    )
    
    role_str_map = {
        UserRole.ADMIN: 'admin',
        UserRole.AUTHORITY_USER: 'authority',
        UserRole.TOWING_COMPANY_USER: 'towing_service'
    }
    
    result = []
    for u in users:
        user_data = {
            'id': u.id,
            'email': u.email,
            'name': u.name,
            'role': role_str_map.get(u.role, 'unknown'),
            'is_blocked': u.isBlocked,
            'blocked': u.isBlocked,
            'created_at': u.createdAt.isoformat() if u.createdAt else None,
            'totp_enabled': u.totpEnabled
        }
        
        if u.authorityUser:
            user_data['authority_name'] = u.authorityUser.authority.name
            user_data['dienstnummer'] = u.authorityUser.dienstnummer
            user_data['approval_status'] = safe_enum_value(u.authorityUser.authority.approvalStatus)
        
        if u.towingCompanyUser:
            user_data['company_name'] = u.towingCompanyUser.towingCompany.companyName
            user_data['service_code'] = u.towingCompanyUser.towingCompany.serviceCode
            user_data['approval_status'] = safe_enum_value(u.towingCompanyUser.towingCompany.approvalStatus)
        
        result.append(user_data)
    
    return result

@api_router.get("/admin/pending-services")
async def get_pending_services(user = Depends(require_admin)):
    services = await prisma.towingcompany.find_many(
        where={'approvalStatus': ApprovalStatus.PENDING},
        include={
            'users': {'include': {'user': True}},
            'pricing': True
        }
    )
    
    result = []
    for s in services:
        main_user = next((u.user for u in s.users if u.isAdmin), None)
        result.append({
            'id': s.id,
            'company_name': s.companyName,
            'phone': s.phone,
            'email': main_user.email if main_user else None,
            'address': s.street,
            'yard_address': s.yardStreet,
            'service_code': s.serviceCode,
            'created_at': s.createdAt.isoformat() if s.createdAt else None,
            'tow_cost': s.pricing.towCost if s.pricing else 0,
            'daily_cost': s.pricing.dailyCost if s.pricing else 0
        })
    
    return result

@api_router.get("/admin/pending-authorities")
async def get_pending_authorities(user = Depends(require_admin)):
    authorities = await prisma.authority.find_many(
        where={'approvalStatus': ApprovalStatus.PENDING},
        include={
            'users': {'include': {'user': True}}
        }
    )
    
    result = []
    for a in authorities:
        main_user = next((u.user for u in a.users if u.isMainAccount), None)
        result.append({
            'id': a.id,
            'authority_name': a.name,
            'department': a.department,
            'email': main_user.email if main_user else None,
            'name': main_user.name if main_user else None,
            'created_at': a.createdAt.isoformat() if a.createdAt else None
        })
    
    return result

@api_router.post("/admin/approve-service/{service_id}")
async def approve_service(service_id: str, data: dict, background_tasks: BackgroundTasks, user = Depends(require_admin)):
    approved = data.get('approved', True)
    rejection_reason = data.get('rejection_reason')
    
    service = await prisma.towingcompany.find_unique(
        where={'id': service_id},
        include={'users': {'include': {'user': True}}}
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Abschleppdienst nicht gefunden")
    
    if approved:
        await prisma.towingcompany.update(
            where={'id': service_id},
            data={
                'approvalStatus': ApprovalStatus.APPROVED,
                'approvedAt': datetime.now(timezone.utc)
            }
        )
        
        main_user = next((u.user for u in service.users if u.isAdmin), None)
        if main_user:
            background_tasks.add_task(
                email_service.send_account_approved_email,
                to_email=main_user.email,
                user_name=main_user.name,
                role='towing_service'
            )
        
        await log_audit("USER_APPROVED", user.id, user.name, user.email, "towing_company", service_id)
    else:
        await prisma.towingcompany.update(
            where={'id': service_id},
            data={
                'approvalStatus': ApprovalStatus.REJECTED,
                'rejectedAt': datetime.now(timezone.utc),
                'rejectionReason': rejection_reason
            }
        )
        await log_audit("USER_REJECTED", user.id, user.name, user.email, "towing_company", service_id, {
            "reason": rejection_reason
        })
    
    return {"message": "Erfolgreich aktualisiert"}

@api_router.post("/admin/approve-authority/{authority_id}")
async def approve_authority(authority_id: str, data: dict, background_tasks: BackgroundTasks, user = Depends(require_admin)):
    approved = data.get('approved', True)
    rejection_reason = data.get('rejection_reason')
    
    authority = await prisma.authority.find_unique(
        where={'id': authority_id},
        include={'users': {'include': {'user': True}}}
    )
    
    if not authority:
        raise HTTPException(status_code=404, detail="Behörde nicht gefunden")
    
    if approved:
        await prisma.authority.update(
            where={'id': authority_id},
            data={
                'approvalStatus': ApprovalStatus.APPROVED,
                'approvedAt': datetime.now(timezone.utc)
            }
        )
        
        main_user = next((u.user for u in authority.users if u.isMainAccount), None)
        if main_user:
            background_tasks.add_task(
                email_service.send_account_approved_email,
                to_email=main_user.email,
                user_name=main_user.name,
                role='authority'
            )
        
        await log_audit("USER_APPROVED", user.id, user.name, user.email, "authority", authority_id)
    else:
        await prisma.authority.update(
            where={'id': authority_id},
            data={
                'approvalStatus': ApprovalStatus.REJECTED,
                'rejectedAt': datetime.now(timezone.utc),
                'rejectionReason': rejection_reason
            }
        )
        await log_audit("USER_REJECTED", user.id, user.name, user.email, "authority", authority_id, {
            "reason": rejection_reason
        })
    
    return {"message": "Erfolgreich aktualisiert"}

@api_router.post("/admin/users/{user_id}/block")
async def block_user(user_id: str, data: dict, admin = Depends(require_admin)):
    blocked = data.get('blocked', True)
    
    target_user = await prisma.user.find_unique(where={'id': user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    
    await prisma.user.update(
        where={'id': user_id},
        data={
            'isBlocked': blocked,
            'blockedAt': datetime.now(timezone.utc) if blocked else None
        }
    )
    
    action = "USER_BLOCKED" if blocked else "USER_UNBLOCKED"
    await log_audit(action, admin.id, admin.name, admin.email, "user", user_id)
    
    return {"message": f"Benutzer {'gesperrt' if blocked else 'entsperrt'}"}

@api_router.get("/admin/audit-logs")
async def get_audit_logs(
    page: int = 1,
    limit: int = 100,
    action: Optional[str] = None,
    user = Depends(require_admin)
):
    skip = (page - 1) * limit
    
    where = {}
    if action:
        action_map = {
            "login": AuditAction.LOGIN,
            "login_failed": AuditAction.LOGIN_FAILED,
            "register": AuditAction.REGISTER,
            "user_approved": AuditAction.USER_APPROVED,
            "user_rejected": AuditAction.USER_REJECTED,
            "job_created": AuditAction.JOB_CREATED,
            "job_status_changed": AuditAction.JOB_STATUS_CHANGED
        }
        if action.lower() in action_map:
            where['action'] = action_map[action.lower()]
    
    logs = await prisma.auditlog.find_many(
        where=where,
        order={'createdAt': 'desc'},
        skip=skip,
        take=limit
    )
    
    total = await prisma.auditlog.count(where=where)
    
    # Return array directly for frontend compatibility
    return [
        {
            "id": log.id,
            "action": safe_enum_value(log.action) if log.action else None,
            "user_id": log.userId,
            "user_email": log.userEmail,
            "user_name": log.userName,
            "entity_type": log.entityType,
            "entity_id": log.entityId,
            "details": log.details,
            "ip_address": log.ipAddress,
            "timestamp": log.createdAt.isoformat() if log.createdAt else None,
            "created_at": log.createdAt.isoformat() if log.createdAt else None
        }
        for log in logs
    ]

@api_router.get("/admin/dsgvo-status")
async def get_dsgvo_status(user = Depends(require_admin)):
    """Get DSGVO data retention status"""
    anonymized_count = await prisma.towingjob.count(where={'personalDataAnonymized': True})
    total_released = await prisma.towingjob.count(where={'status': JobStatus.RELEASED})
    
    return {
        "dsgvo": {
            "retention_days": DSGVO_RETENTION_DAYS,
            "retention_months": DSGVO_RETENTION_DAYS // 30,
            "description": "Personenbezogene Daten werden nach 6 Monaten anonymisiert"
        },
        "steuerrecht": {
            "retention_years": INVOICE_RETENTION_YEARS,
            "legal_basis": "§ 147 AO / § 257 HGB",
            "description": "Rechnungsdaten werden 10 Jahre aufbewahrt"
        },
        "stats": {
            "anonymized_jobs": anonymized_count,
            "total_released_jobs": total_released
        },
        "scheduler_running": scheduler.running
    }

@api_router.post("/admin/trigger-cleanup")
async def trigger_dsgvo_cleanup(user = Depends(require_admin)):
    """Manually trigger DSGVO cleanup"""
    result = await dsgvo_data_cleanup()
    
    await log_audit("DSGVO_PERSONAL_DATA_CLEANUP", user.id, user.name, user.email, None, None, {
        "triggered_by": "admin",
        "personal_data_retention_days": DSGVO_RETENTION_DAYS,
        "invoice_retention_years": INVOICE_RETENTION_YEARS,
        "note": "Rechnungsdaten bleiben erhalten (§ 147 AO)"
    })
    
    return {
        "message": "DSGVO-Cleanup durchgeführt",
        "personal_data_retention_days": DSGVO_RETENTION_DAYS,
        "invoice_retention_years": INVOICE_RETENTION_YEARS,
        "note": "Personenbezogene Daten anonymisiert, Rechnungsdaten bleiben erhalten (§ 147 AO / § 257 HGB)",
        "result": result
    }

# ============================================================================
# DSGVO CLEANUP FUNCTION
# ============================================================================

async def dsgvo_data_cleanup():
    """Anonymize personal data after retention period"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=DSGVO_RETENTION_DAYS)
        
        # Find jobs to anonymize
        jobs_to_anonymize = await prisma.towingjob.find_many(
            where={
                'status': JobStatus.RELEASED,
                'releasedAt': {'lt': cutoff_date},
                'personalDataAnonymized': False
            }
        )
        
        anonymized_count = 0
        for job in jobs_to_anonymize:
            await prisma.towingjob.update(
                where={'id': job.id},
                data={
                    'licensePlate': '*** (DSGVO-Anonymisiert)',
                    'vin': '*** (DSGVO-Anonymisiert)',
                    'ownerFirstName': '***',
                    'ownerLastName': '***',
                    'ownerStreet': '***',
                    'ownerCity': '***',
                    'ownerZipCode': '***',
                    'ownerPhone': '***',
                    'ownerEmail': '***',
                    'personalDataAnonymized': True,
                    'personalDataAnonymizedAt': datetime.now(timezone.utc)
                }
            )
            
            # Delete photos
            photos = await prisma.towingjobphoto.find_many(where={'jobId': job.id})
            for photo in photos:
                await prisma.towingjobphoto.update(
                    where={'id': photo.id},
                    data={
                        'isDeleted': True,
                        'deletedAt': datetime.now(timezone.utc)
                    }
                )
            
            anonymized_count += 1
        
        logger.info(f"✅ DSGVO Cleanup: {anonymized_count} Aufträge anonymisiert")
        return {"anonymized_count": anonymized_count}
        
    except Exception as e:
        logger.error(f"❌ DSGVO Cleanup failed: {e}")
        return {"error": str(e)}

# ============================================================================
# JOB ROUTES
# ============================================================================

@api_router.get("/jobs")
async def get_jobs(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get jobs based on user role"""
    skip = (page - 1) * limit
    where = {}
    
    # Role-based filtering
    if user.role == UserRole.AUTHORITY_USER:
        if user.authorityUser:
            where['authorityId'] = user.authorityUser.authorityId
    elif user.role == UserRole.TOWING_COMPANY_USER:
        if user.towingCompanyUser:
            where['towingCompanyId'] = user.towingCompanyUser.towingCompanyId
    
    # Status filter
    if status:
        status_map = {
            'pending': JobStatus.PENDING,
            'assigned': JobStatus.ASSIGNED,
            'on_site': JobStatus.ON_SITE,
            'towed': JobStatus.TOWED,
            'in_yard': JobStatus.IN_YARD,
            'released': JobStatus.RELEASED,
            'cancelled': JobStatus.CANCELLED
        }
        if status.lower() in status_map:
            where['status'] = status_map[status.lower()]
    
    # Search filter
    if search:
        where['OR'] = [
            {'licensePlate': {'contains': search, 'mode': 'insensitive'}},
            {'vin': {'contains': search, 'mode': 'insensitive'}},
            {'jobNumber': {'contains': search, 'mode': 'insensitive'}},
            {'towReason': {'contains': search, 'mode': 'insensitive'}},
            {'locationAddress': {'contains': search, 'mode': 'insensitive'}}
        ]
    
    jobs = await prisma.towingjob.find_many(
        where=where,
        include={
            'authority': True,
            'towingCompany': True,
            'photos': True,
            'createdByUser': {'include': {'user': True}}
        },
        order={'createdAt': 'desc'},
        skip=skip,
        take=limit
    )
    
    result = []
    for job in jobs:
        job_data = {
            'id': job.id,
            'job_number': job.jobNumber,
            'license_plate': job.licensePlate,
            'vin': job.vin,
            'tow_reason': job.towReason,
            'location_address': job.locationAddress,
            'location_lat': job.locationLat,
            'location_lng': job.locationLng,
            'status': safe_enum_value(job.status, 'pending'),
            'job_type': safe_enum_value(job.jobType, 'towing'),
            'authority_notes': job.authorityNotes,
            'service_notes': job.serviceNotes,
            'notes': job.authorityNotes,
            'created_at': job.createdAt.isoformat() if job.createdAt else None,
            'updated_at': job.updatedAt.isoformat() if job.updatedAt else None,
            'assigned_at': job.assignedAt.isoformat() if job.assignedAt else None,
            'accepted_at': job.acceptedAt.isoformat() if job.acceptedAt else None,
            'on_site_at': job.onSiteAt.isoformat() if job.onSiteAt else None,
            'towed_at': job.towedAt.isoformat() if job.towedAt else None,
            'in_yard_at': job.inYardAt.isoformat() if job.inYardAt else None,
            'released_at': job.releasedAt.isoformat() if job.releasedAt else None,
            'authority_id': job.authorityId,
            'assigned_service_id': job.towingCompanyId,
            'is_empty_trip': job.isEmptyTrip,
            'owner_first_name': job.ownerFirstName,
            'owner_last_name': job.ownerLastName,
            'owner_address': job.ownerStreet,
            'payment_method': safe_enum_value(job.paymentMethod) if job.paymentMethod else None,
            'payment_amount': job.paymentAmount,
            'calculated_costs': job.calculatedCosts,
            'personal_data_anonymized': job.personalDataAnonymized,
            'sicherstellung_reason': job.sicherstellungReason,
            'vehicle_category': safe_enum_value(job.vehicleCategory) if job.vehicleCategory else None,
            'ordering_authority': job.orderingAuthority,
            'contact_attempts': job.contactAttempts,
            'contact_attempts_notes': job.contactAttemptsNotes,
            'estimated_vehicle_value': job.estimatedVehicleValue
        }
        
        # Add authority info
        if job.authority:
            job_data['created_by_authority'] = job.authority.name
        
        # Add service info
        if job.towingCompany:
            job_data['assigned_service_name'] = job.towingCompany.companyName
        
        # Add creator info
        if job.createdByUser and job.createdByUser.user:
            job_data['created_by_name'] = job.createdByUser.user.name
            job_data['created_by_id'] = job.createdByUser.userId
            job_data['created_by_dienstnummer'] = job.createdByUser.dienstnummer
        
        # Add photos
        authority_photos = []
        service_photos = []
        for photo in job.photos:
            if not photo.isDeleted:
                if photo.photoType == PhotoType.AUTHORITY_PHOTO:
                    authority_photos.append(photo.storagePath)
                else:
                    service_photos.append(photo.storagePath)
        job_data['photos'] = authority_photos
        job_data['service_photos'] = service_photos
        
        result.append(job_data)
    
    return result

@api_router.get("/jobs/count/total")
async def get_jobs_count(user = Depends(get_current_user)):
    """Get total job count for current user"""
    where = {}
    
    if user.role == UserRole.AUTHORITY_USER and user.authorityUser:
        where['authorityId'] = user.authorityUser.authorityId
    elif user.role == UserRole.TOWING_COMPANY_USER and user.towingCompanyUser:
        where['towingCompanyId'] = user.towingCompanyUser.towingCompanyId
    
    count = await prisma.towingjob.count(where=where)
    return {"total": count}

@api_router.get("/jobs/updates")
async def get_job_updates_polling(since: Optional[str] = None, user = Depends(get_current_user)):
    """Get recent job updates for polling - MUST be before /jobs/{job_id}"""
    where = {}
    
    if user.role == UserRole.AUTHORITY_USER and user.authorityUser:
        where['authorityId'] = user.authorityUser.authorityId
    elif user.role == UserRole.TOWING_COMPANY_USER and user.towingCompanyUser:
        where['towingCompanyId'] = user.towingCompanyUser.towingCompanyId
    
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            where['updatedAt'] = {'gt': since_dt}
        except:
            pass
    
    jobs = await prisma.towingjob.find_many(
        where=where,
        order={'updatedAt': 'desc'},
        take=50
    )
    
    return [{
        'id': j.id,
        'job_number': j.jobNumber,
        'status': safe_enum_value(j.status),
        'updated_at': j.updatedAt.isoformat() if j.updatedAt else None
    } for j in jobs]

@api_router.get("/admin/jobs")
async def get_admin_jobs(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    user = Depends(require_admin)
):
    """Get all jobs for admin"""
    skip = (page - 1) * limit
    where = {}
    
    if status:
        status_map = {
            'pending': JobStatus.PENDING,
            'assigned': JobStatus.ASSIGNED,
            'on_site': JobStatus.ON_SITE,
            'towed': JobStatus.TOWED,
            'in_yard': JobStatus.IN_YARD,
            'released': JobStatus.RELEASED
        }
        if status.lower() in status_map:
            where['status'] = status_map[status.lower()]
    
    if search:
        where['OR'] = [
            {'licensePlate': {'contains': search, 'mode': 'insensitive'}},
            {'vin': {'contains': search, 'mode': 'insensitive'}},
            {'jobNumber': {'contains': search, 'mode': 'insensitive'}},
            {'towReason': {'contains': search, 'mode': 'insensitive'}},
            {'locationAddress': {'contains': search, 'mode': 'insensitive'}}
        ]
    
    jobs = await prisma.towingjob.find_many(
        where=where,
        include={
            'authority': True,
            'towingCompany': True
        },
        order={'createdAt': 'desc'},
        skip=skip,
        take=limit
    )
    
    return [{
        'id': j.id,
        'job_number': j.jobNumber,
        'license_plate': j.licensePlate,
        'vin': j.vin,
        'tow_reason': j.towReason,
        'location_address': j.locationAddress,
        'status': safe_enum_value(j.status, 'pending'),
        'created_at': j.createdAt.isoformat() if j.createdAt else None,
        'created_by_authority': j.authority.name if j.authority else None,
        'assigned_service_name': j.towingCompany.companyName if j.towingCompany else None,
        'personal_data_anonymized': j.personalDataAnonymized
    } for j in jobs]

@api_router.get("/admin/jobs/count")
async def get_admin_jobs_count(user = Depends(require_admin)):
    count = await prisma.towingjob.count()
    return {"total": count}

@api_router.post("/jobs")
async def create_job(data: JobCreate, user = Depends(get_current_user)):
    """Create a new towing job"""
    
    # Determine authority_id based on user role
    if user.role == UserRole.AUTHORITY_USER:
        if not user.authorityUser:
            raise HTTPException(status_code=400, detail="Authority user not configured")
        authority_id = user.authorityUser.authorityId
        created_by_service = False
    elif user.role == UserRole.TOWING_COMPANY_USER:
        if not data.for_authority_id:
            raise HTTPException(status_code=400, detail="for_authority_id erforderlich")
        authority_id = data.for_authority_id
        created_by_service = True
    else:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    
    # Check for duplicate license plate
    if data.license_plate:
        existing = await prisma.towingjob.find_first(
            where={
                'licensePlate': data.license_plate,
                'status': {'notIn': [JobStatus.RELEASED, JobStatus.CANCELLED]}
            }
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ein Fahrzeug mit diesem Kennzeichen ({data.license_plate}) ist bereits im System und wurde noch nicht freigegeben. Status: {safe_enum_value(existing.status)}"
            )
    
    # Map job type
    job_type = JobType.SICHERSTELLUNG if data.job_type == 'sicherstellung' else JobType.TOWING
    
    # Map vehicle category
    vehicle_category = None
    if data.vehicle_category:
        vehicle_category = VehicleCategory.OVER_3_5T if data.vehicle_category == 'over_3_5t' else VehicleCategory.UNDER_3_5T
    
    # Create job
    job = await prisma.towingjob.create(
        data={
            'jobNumber': generate_job_number(),
            'licensePlate': data.license_plate,
            'vin': data.vin,
            'towReason': data.tow_reason,
            'locationAddress': data.location_address,
            'locationLat': data.location_lat,
            'locationLng': data.location_lng,
            'authorityNotes': data.notes,
            'status': JobStatus.ASSIGNED if data.assigned_service_id else JobStatus.PENDING,
            'jobType': job_type,
            'authorityId': authority_id,
            'createdByUserId': user.authorityUser.id if user.authorityUser else None,
            'createdByServiceFlag': created_by_service,
            'towingCompanyId': data.assigned_service_id,
            'assignedAt': datetime.now(timezone.utc) if data.assigned_service_id else None,
            'sicherstellungReason': data.sicherstellung_reason,
            'vehicleCategory': vehicle_category,
            'orderingAuthority': data.ordering_authority,
            'contactAttempts': data.contact_attempts,
            'contactAttemptsNotes': data.contact_attempts_notes,
            'estimatedVehicleValue': data.estimated_vehicle_value
        }
    )
    
    # Add photos
    for i, photo in enumerate(data.photos[:5]):  # Max 5 photos
        compressed = compress_image_base64(photo)
        await prisma.towingjobphoto.create(
            data={
                'jobId': job.id,
                'photoType': PhotoType.AUTHORITY_PHOTO,
                'storagePath': compressed,
                'uploadedByUserId': user.id
            }
        )
    
    # Create event
    await prisma.towingjob.create(
        data={
            'jobId': job.id,
            'eventType': 'JOB_CREATED',
            'toStatus': job.status,
            'description': 'Auftrag erstellt',
            'triggeredByUserId': user.id,
            'triggeredByName': user.name
        }
    ) if False else None  # Skip for now
    
    await log_audit("JOB_CREATED", user.id, user.name, user.email, "job", job.id, {
        "job_number": job.jobNumber,
        "license_plate": data.license_plate
    })
    
    return {
        'id': job.id,
        'job_number': job.jobNumber,
        'status': safe_enum_value(job.status),
        'message': 'Auftrag erfolgreich erstellt'
    }

@api_router.get("/jobs/{job_id}")
async def get_job(job_id: str, user = Depends(get_current_user)):
    """Get a single job by ID"""
    job = await prisma.towingjob.find_unique(
        where={'id': job_id},
        include={
            'authority': True,
            'towingCompany': {'include': {'pricing': True}},
            'photos': True,
            'createdByUser': {'include': {'user': True}}
        }
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    # Build response
    response = {
        'id': job.id,
        'job_number': job.jobNumber,
        'license_plate': job.licensePlate,
        'vin': job.vin,
        'tow_reason': job.towReason,
        'location_address': job.locationAddress,
        'location_lat': job.locationLat,
        'location_lng': job.locationLng,
        'status': safe_enum_value(job.status, 'pending'),
        'job_type': safe_enum_value(job.jobType, 'towing'),
        'authority_notes': job.authorityNotes,
        'service_notes': job.serviceNotes,
        'notes': job.authorityNotes,
        'created_at': job.createdAt.isoformat() if job.createdAt else None,
        'updated_at': job.updatedAt.isoformat() if job.updatedAt else None,
        'accepted_at': job.acceptedAt.isoformat() if job.acceptedAt else None,
        'on_site_at': job.onSiteAt.isoformat() if job.onSiteAt else None,
        'towed_at': job.towedAt.isoformat() if job.towedAt else None,
        'in_yard_at': job.inYardAt.isoformat() if job.inYardAt else None,
        'released_at': job.releasedAt.isoformat() if job.releasedAt else None,
        'is_empty_trip': job.isEmptyTrip,
        'owner_first_name': job.ownerFirstName,
        'owner_last_name': job.ownerLastName,
        'owner_address': job.ownerStreet,
        'payment_method': safe_enum_value(job.paymentMethod) if job.paymentMethod else None,
        'payment_amount': job.paymentAmount,
        'calculated_costs': job.calculatedCosts,
        'sicherstellung_reason': job.sicherstellungReason,
        'vehicle_category': safe_enum_value(job.vehicleCategory) if job.vehicleCategory else None,
        'ordering_authority': job.orderingAuthority,
        'contact_attempts': job.contactAttempts,
        'contact_attempts_notes': job.contactAttemptsNotes,
        'estimated_vehicle_value': job.estimatedVehicleValue
    }
    
    if job.authority:
        response['authority_id'] = job.authorityId
        response['created_by_authority'] = job.authority.name
    
    if job.towingCompany:
        response['assigned_service_id'] = job.towingCompanyId
        response['assigned_service_name'] = job.towingCompany.companyName
    
    if job.createdByUser and job.createdByUser.user:
        response['created_by_id'] = job.createdByUser.userId
        response['created_by_name'] = job.createdByUser.user.name
        response['created_by_dienstnummer'] = job.createdByUser.dienstnummer
    
    # Photos
    authority_photos = []
    service_photos = []
    for photo in job.photos:
        if not photo.isDeleted:
            if photo.photoType == PhotoType.AUTHORITY_PHOTO:
                authority_photos.append(photo.storagePath)
            else:
                service_photos.append(photo.storagePath)
    response['photos'] = authority_photos
    response['service_photos'] = service_photos
    
    return response

@api_router.put("/jobs/{job_id}")
async def update_job(job_id: str, data: JobUpdate, user = Depends(get_current_user)):
    """Update job status and details"""
    job = await prisma.towingjob.find_unique(where={'id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    update_data = {}
    
    # Status update
    if data.status:
        status_map = {
            'pending': JobStatus.PENDING,
            'assigned': JobStatus.ASSIGNED,
            'on_site': JobStatus.ON_SITE,
            'towed': JobStatus.TOWED,
            'in_yard': JobStatus.IN_YARD,
            'released': JobStatus.RELEASED,
            'cancelled': JobStatus.CANCELLED
        }
        new_status = status_map.get(data.status.lower())
        if new_status:
            update_data['status'] = new_status
            
            # Set timestamps based on status
            now = datetime.now(timezone.utc)
            if new_status == JobStatus.ASSIGNED and not job.assignedAt:
                update_data['assignedAt'] = now
                update_data['acceptedAt'] = now
            elif new_status == JobStatus.ON_SITE and not job.onSiteAt:
                update_data['onSiteAt'] = now
            elif new_status == JobStatus.TOWED and not job.towedAt:
                update_data['towedAt'] = now
            elif new_status == JobStatus.IN_YARD and not job.inYardAt:
                update_data['inYardAt'] = now
            elif new_status == JobStatus.RELEASED and not job.releasedAt:
                update_data['releasedAt'] = now
    
    # Other updates
    if data.service_notes is not None:
        update_data['serviceNotes'] = data.service_notes
    if data.notes is not None:
        update_data['authorityNotes'] = data.notes
    if data.owner_first_name is not None:
        update_data['ownerFirstName'] = data.owner_first_name
    if data.owner_last_name is not None:
        update_data['ownerLastName'] = data.owner_last_name
    if data.owner_address is not None:
        update_data['ownerStreet'] = data.owner_address
    if data.payment_method is not None:
        payment_map = {
            'cash': PaymentMethod.CASH,
            'card': PaymentMethod.CARD,
            'invoice': PaymentMethod.INVOICE
        }
        update_data['paymentMethod'] = payment_map.get(data.payment_method.lower())
    if data.payment_amount is not None:
        update_data['paymentAmount'] = data.payment_amount
    if data.is_empty_trip is not None:
        update_data['isEmptyTrip'] = data.is_empty_trip
    
    # Update job
    updated_job = await prisma.towingjob.update(
        where={'id': job_id},
        data=update_data
    )
    
    # Add service photos if provided
    if data.photos:
        for photo in data.photos[:5]:
            compressed = compress_image_base64(photo)
            await prisma.towingjobphoto.create(
                data={
                    'jobId': job_id,
                    'photoType': PhotoType.SERVICE_PHOTO,
                    'storagePath': compressed,
                    'uploadedByUserId': user.id
                }
            )
    
    await log_audit("JOB_STATUS_CHANGED", user.id, user.name, user.email, "job", job_id, {
        "old_status": safe_enum_value(job.status) if job.status else None,
        "new_status": data.status
    })
    
    return {"message": "Auftrag aktualisiert", "status": safe_enum_value(updated_job.status)}

@api_router.patch("/jobs/{job_id}/edit-data")
async def edit_job_data(job_id: str, data: JobEditData, user = Depends(get_current_user)):
    """Edit job vehicle data (license plate, VIN, etc.)"""
    job = await prisma.towingjob.find_unique(where={'id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    # Cannot edit released or cancelled jobs
    if job.status in [JobStatus.RELEASED, JobStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Freigegebene oder stornierte Aufträge können nicht bearbeitet werden")
    
    update_data = {}
    changes = {}
    
    if data.license_plate is not None and data.license_plate != job.licensePlate:
        update_data['licensePlate'] = data.license_plate
        changes['license_plate'] = {'old': job.licensePlate, 'new': data.license_plate}
    
    if data.vin is not None and data.vin != job.vin:
        update_data['vin'] = data.vin
        changes['vin'] = {'old': job.vin, 'new': data.vin}
    
    if data.tow_reason is not None and data.tow_reason != job.towReason:
        update_data['towReason'] = data.tow_reason
        changes['tow_reason'] = {'old': job.towReason, 'new': data.tow_reason}
    
    if data.notes is not None:
        update_data['authorityNotes'] = data.notes
    
    if data.location_address is not None:
        update_data['locationAddress'] = data.location_address
    if data.location_lat is not None:
        update_data['locationLat'] = data.location_lat
    if data.location_lng is not None:
        update_data['locationLng'] = data.location_lng
    
    if update_data:
        await prisma.towingjob.update(
            where={'id': job_id},
            data=update_data
        )
        
        await log_audit("JOB_UPDATED", user.id, user.name, user.email, "job", job_id, {
            "changes": changes,
            "action": "JOB_DATA_EDITED"
        })
    
    return {"message": "Auftragsdaten aktualisiert", "changes": changes}

@api_router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user = Depends(get_current_user)):
    """Delete a job"""
    job = await prisma.towingjob.find_unique(where={'id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    # Only allow deletion of pending/cancelled jobs or by admin
    if user.role != UserRole.ADMIN and job.status not in [JobStatus.PENDING, JobStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Nur ausstehende Aufträge können gelöscht werden")
    
    # Delete photos first
    await prisma.towingjobphoto.delete_many(where={'jobId': job_id})
    
    # Delete events
    await prisma.towingjob.delete_many(where={'id': job_id})
    
    # Delete job
    await prisma.towingjob.delete(where={'id': job_id})
    
    await log_audit("JOB_UPDATED", user.id, user.name, user.email, "job", job_id, {
        "action": "JOB_DELETED",
        "job_number": job.jobNumber
    })
    
    return {"message": "Auftrag gelöscht"}

@api_router.get("/jobs/{job_id}/calculate-costs")
async def calculate_job_costs(job_id: str, user = Depends(get_current_user)):
    """Calculate costs for a job"""
    job = await prisma.towingjob.find_unique(
        where={'id': job_id},
        include={'towingCompany': {'include': {'pricing': True}}}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    if not job.towingCompany or not job.towingCompany.pricing:
        return {"message": "Keine Preiskonfiguration verfügbar", "total": 0}
    
    pricing = job.towingCompany.pricing
    breakdown = []
    total = 0
    
    # Time-based calculation
    if pricing.timeBasedEnabled and pricing.firstHalfHour and job.acceptedAt and job.inYardAt:
        duration_minutes = (job.inYardAt - job.acceptedAt).total_seconds() / 60
        half_hours = max(1, math.ceil(duration_minutes / 30))
        
        first_half = pricing.firstHalfHour
        breakdown.append({"label": "Erste halbe Stunde", "amount": first_half})
        total += first_half
        
        if half_hours > 1 and pricing.additionalHalfHour:
            additional = (half_hours - 1) * pricing.additionalHalfHour
            breakdown.append({"label": f"Weitere {half_hours - 1} halbe Stunde(n)", "amount": additional})
            total += additional
    else:
        # Standard tow cost
        if pricing.towCost:
            breakdown.append({"label": "Abschleppkosten", "amount": pricing.towCost})
            total += pricing.towCost
    
    # Daily cost
    if pricing.dailyCost and job.inYardAt:
        days = calculate_days_in_yard(job.inYardAt)
        daily_total = pricing.dailyCost * days
        breakdown.append({"label": f"Standgebühr ({days} Tag(e))", "amount": daily_total})
        total += daily_total
    
    # Processing fee
    if pricing.processingFee:
        breakdown.append({"label": "Bearbeitungsgebühr", "amount": pricing.processingFee})
        total += pricing.processingFee
    
    # Empty trip fee
    if job.isEmptyTrip and pricing.emptyTripFee:
        breakdown.append({"label": "Leerfahrt", "amount": pricing.emptyTripFee})
        total += pricing.emptyTripFee
    
    return {
        "breakdown": breakdown,
        "total": round(total, 2),
        "days_in_yard": calculate_days_in_yard(job.inYardAt) if job.inYardAt else 0
    }

# ============================================================================
# PUBLIC SEARCH
# ============================================================================

@api_router.get("/search/vehicle")
async def search_vehicle(q: str):
    """Public vehicle search by license plate or VIN"""
    if not q or len(q) < 3:
        raise HTTPException(status_code=400, detail="Suchbegriff zu kurz (mindestens 3 Zeichen)")
    
    # Search for vehicle
    job = await prisma.towingjob.find_first(
        where={
            'OR': [
                {'licensePlate': {'contains': q.upper(), 'mode': 'insensitive'}},
                {'vin': {'contains': q.upper(), 'mode': 'insensitive'}}
            ],
            'status': {'notIn': [JobStatus.RELEASED, JobStatus.CANCELLED]},
            'personalDataAnonymized': False
        },
        include={
            'towingCompany': {'include': {'pricing': True}}
        },
        order={'createdAt': 'desc'}
    )
    
    if not job:
        return {"found": False, "message": "Kein Fahrzeug gefunden"}
    
    response = {
        "found": True,
        "job_number": job.jobNumber,
        "license_plate": job.licensePlate,
        "status": safe_enum_value(job.status, 'pending'),
        "towed_at": job.towedAt.isoformat() if job.towedAt else None,
        "in_yard_at": job.inYardAt.isoformat() if job.inYardAt else None,
        "tow_reason": job.towReason,
        "location_address": job.locationAddress,
        "location_lat": job.locationLat,
        "location_lng": job.locationLng
    }
    
    if job.towingCompany:
        tc = job.towingCompany
        response["company_name"] = tc.companyName
        response["phone"] = tc.phone
        response["email"] = tc.email
        response["yard_address"] = tc.yardStreet
        response["yard_lat"] = tc.yardLat
        response["yard_lng"] = tc.yardLng
        response["opening_hours"] = tc.openingHours
        
        if tc.pricing:
            response["tow_cost"] = tc.pricing.towCost
            response["daily_cost"] = tc.pricing.dailyCost
            response["processing_fee"] = tc.pricing.processingFee
            
            # Calculate total cost
            days = calculate_days_in_yard(job.inYardAt) if job.inYardAt else 1
            total = (tc.pricing.towCost or 0) + (tc.pricing.dailyCost or 0) * days + (tc.pricing.processingFee or 0)
            response["days_in_yard"] = days
            response["total_cost"] = round(total, 2)
    
    return response

# ============================================================================
# SERVICES ROUTES
# ============================================================================

@api_router.get("/services")
async def get_linked_services(user = Depends(get_current_user)):
    """Get services linked to current authority"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    links = await prisma.authoritytowingcompanylink.find_many(
        where={'authorityId': user.authorityUser.authorityId},
        include={'towingCompany': {'include': {'pricing': True}}}
    )
    
    return [{
        'id': link.towingCompany.id,
        'company_name': link.towingCompany.companyName,
        'phone': link.towingCompany.phone,
        'address': link.towingCompany.street,
        'yard_address': link.towingCompany.yardStreet,
        'service_code': link.towingCompany.serviceCode,
        'tow_cost': link.towingCompany.pricing.towCost if link.towingCompany.pricing else 0,
        'daily_cost': link.towingCompany.pricing.dailyCost if link.towingCompany.pricing else 0,
        'linked_at': link.linkedAt.isoformat() if link.linkedAt else None
    } for link in links]

@api_router.post("/services/link")
async def link_service(data: LinkServiceRequest, user = Depends(get_current_user)):
    """Link a towing service by code"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    if not user.authorityUser.isMainAccount:
        raise HTTPException(status_code=403, detail="Nur Haupt-Accounts können Dienste verknüpfen")
    
    # Find service by code
    service = await prisma.towingcompany.find_unique(
        where={'serviceCode': data.service_code}
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Abschleppdienst nicht gefunden")
    
    if service.approvalStatus != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Abschleppdienst noch nicht freigeschaltet")
    
    # Check if already linked
    existing = await prisma.authoritytowingcompanylink.find_first(
        where={
            'authorityId': user.authorityUser.authorityId,
            'towingCompanyId': service.id
        }
    )
    
    if existing:
        raise HTTPException(status_code=400, detail="Abschleppdienst bereits verknüpft")
    
    # Create link
    await prisma.authoritytowingcompanylink.create(
        data={
            'authorityId': user.authorityUser.authorityId,
            'towingCompanyId': service.id,
            'linkedByUserId': user.id
        }
    )
    
    await log_audit("SERVICE_LINKED", user.id, user.name, user.email, "towing_company", service.id, {
        "authority_id": user.authorityUser.authorityId,
        "service_code": data.service_code
    })
    
    return {"message": "Abschleppdienst erfolgreich verknüpft", "service_id": service.id}

@api_router.delete("/services/unlink/{service_id}")
async def unlink_service(service_id: str, user = Depends(get_current_user)):
    """Unlink a towing service"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    if not user.authorityUser.isMainAccount:
        raise HTTPException(status_code=403, detail="Nur Haupt-Accounts können Dienste entfernen")
    
    await prisma.authoritytowingcompanylink.delete_many(
        where={
            'authorityId': user.authorityUser.authorityId,
            'towingCompanyId': service_id
        }
    )
    
    await log_audit("SERVICE_UNLINKED", user.id, user.name, user.email, "towing_company", service_id)
    
    return {"message": "Verknüpfung entfernt"}

@api_router.get("/towing/linked-authorities")
async def get_linked_authorities(user = Depends(get_current_user)):
    """Get authorities linked to current towing service"""
    if user.role != UserRole.TOWING_COMPANY_USER or not user.towingCompanyUser:
        raise HTTPException(status_code=403, detail="Nur für Abschleppdienste")
    
    links = await prisma.authoritytowingcompanylink.find_many(
        where={'towingCompanyId': user.towingCompanyUser.towingCompanyId},
        include={'authority': True}
    )
    
    return [{
        'id': link.authority.id,
        'name': link.authority.name,
        'department': link.authority.department,
        'linked_at': link.linkedAt.isoformat() if link.linkedAt else None
    } for link in links]

@api_router.patch("/services/pricing-settings")
async def update_pricing_settings(data: PricingSettingsRequest, user = Depends(get_current_user)):
    """Update pricing settings for towing service"""
    if user.role != UserRole.TOWING_COMPANY_USER or not user.towingCompanyUser:
        raise HTTPException(status_code=403, detail="Nur für Abschleppdienste")
    
    update_data = {}
    if data.time_based_enabled is not None:
        update_data['timeBasedEnabled'] = data.time_based_enabled
    if data.first_half_hour is not None:
        update_data['firstHalfHour'] = data.first_half_hour
    if data.additional_half_hour is not None:
        update_data['additionalHalfHour'] = data.additional_half_hour
    if data.tow_cost is not None:
        update_data['towCost'] = data.tow_cost
    if data.daily_cost is not None:
        update_data['dailyCost'] = data.daily_cost
    if data.processing_fee is not None:
        update_data['processingFee'] = data.processing_fee
    if data.empty_trip_fee is not None:
        update_data['emptyTripFee'] = data.empty_trip_fee
    if data.night_surcharge is not None:
        update_data['nightSurcharge'] = data.night_surcharge
    if data.weekend_surcharge is not None:
        update_data['weekendSurcharge'] = data.weekend_surcharge
    if data.heavy_vehicle_surcharge is not None:
        update_data['heavyVehicleSurcharge'] = data.heavy_vehicle_surcharge
    
    await prisma.towingcompanypricing.update(
        where={'towingCompanyId': user.towingCompanyUser.towingCompanyId},
        data=update_data
    )
    
    await log_audit("SETTINGS_UPDATED", user.id, user.name, user.email, "pricing", user.towingCompanyUser.towingCompanyId)
    
    return {"message": "Preiseinstellungen aktualisiert"}

# ============================================================================
# EMPLOYEE ROUTES
# ============================================================================

@api_router.get("/authority/employees")
async def get_employees(user = Depends(get_current_user)):
    """Get employees of current authority"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    if not user.authorityUser.isMainAccount:
        raise HTTPException(status_code=403, detail="Nur Haupt-Accounts können Mitarbeiter sehen")
    
    employees = await prisma.authorityuser.find_many(
        where={
            'authorityId': user.authorityUser.authorityId,
            'isMainAccount': False
        },
        include={'user': True}
    )
    
    return [{
        'id': emp.userId,
        'email': emp.user.email,
        'name': emp.user.name,
        'dienstnummer': emp.dienstnummer,
        'is_blocked': emp.user.isBlocked,
        'created_at': emp.user.createdAt.isoformat() if emp.user.createdAt else None
    } for emp in employees]

@api_router.post("/authority/employees")
async def create_employee(data: CreateEmployeeRequest, user = Depends(get_current_user)):
    """Create a new employee account"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    if not user.authorityUser.isMainAccount:
        raise HTTPException(status_code=403, detail="Nur Haupt-Accounts können Mitarbeiter erstellen")
    
    # Check email uniqueness
    existing = await prisma.user.find_unique(where={'email': data.email})
    if existing:
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    
    # Validate password
    is_valid, error_msg = validate_password(data.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Create user
    new_user = await prisma.user.create(
        data={
            'email': data.email,
            'passwordHash': hash_password(data.password),
            'role': UserRole.AUTHORITY_USER,
            'name': data.name
        }
    )
    
    # Create authority user
    dienstnummer = await generate_dienstnummer(user.authorityUser.authorityId)
    await prisma.authorityuser.create(
        data={
            'userId': new_user.id,
            'authorityId': user.authorityUser.authorityId,
            'dienstnummer': dienstnummer,
            'isMainAccount': False,
            'parentUserId': user.authorityUser.id
        }
    )
    
    await log_audit("EMPLOYEE_CREATED", user.id, user.name, user.email, "user", new_user.id, {
        "employee_email": data.email,
        "dienstnummer": dienstnummer
    })
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "dienstnummer": dienstnummer,
        "message": "Mitarbeiter erfolgreich erstellt"
    }

@api_router.delete("/authority/employees/{employee_id}")
async def delete_employee(employee_id: str, user = Depends(get_current_user)):
    """Delete an employee"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    if not user.authorityUser.isMainAccount:
        raise HTTPException(status_code=403, detail="Nur Haupt-Accounts können Mitarbeiter löschen")
    
    # Verify employee belongs to this authority
    employee = await prisma.authorityuser.find_first(
        where={
            'userId': employee_id,
            'authorityId': user.authorityUser.authorityId,
            'isMainAccount': False
        }
    )
    
    if not employee:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    
    # Delete authority user link
    await prisma.authorityuser.delete(where={'id': employee.id})
    
    # Delete user
    await prisma.user.delete(where={'id': employee_id})
    
    await log_audit("EMPLOYEE_DELETED", user.id, user.name, user.email, "user", employee_id)
    
    return {"message": "Mitarbeiter gelöscht"}

@api_router.patch("/authority/employees/{employee_id}/block")
async def block_employee(employee_id: str, data: dict, user = Depends(get_current_user)):
    """Block/unblock an employee"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    if not user.authorityUser.isMainAccount:
        raise HTTPException(status_code=403, detail="Nur Haupt-Accounts können Mitarbeiter sperren")
    
    blocked = data.get('blocked', True)
    
    await prisma.user.update(
        where={'id': employee_id},
        data={
            'isBlocked': blocked,
            'blockedAt': datetime.now(timezone.utc) if blocked else None
        }
    )
    
    return {"message": f"Mitarbeiter {'gesperrt' if blocked else 'entsperrt'}"}

# ============================================================================
# EXPORT ROUTES
# ============================================================================

@api_router.get("/export/jobs/excel")
async def export_jobs_excel(user = Depends(get_current_user)):
    """Export jobs to Excel"""
    where = {}
    if user.role == UserRole.AUTHORITY_USER and user.authorityUser:
        where['authorityId'] = user.authorityUser.authorityId
    elif user.role == UserRole.TOWING_COMPANY_USER and user.towingCompanyUser:
        where['towingCompanyId'] = user.towingCompanyUser.towingCompanyId
    
    jobs = await prisma.towingjob.find_many(
        where=where,
        include={'authority': True, 'towingCompany': True},
        order={'createdAt': 'desc'}
    )
    
    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aufträge"
    
    # Headers
    headers = ["Auftragsnummer", "Kennzeichen", "FIN", "Status", "Abschleppgrund", "Standort", "Behörde", "Abschleppdienst", "Erstellt am"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
    
    # Data
    for row, job in enumerate(jobs, 2):
        ws.cell(row=row, column=1, value=job.jobNumber)
        ws.cell(row=row, column=2, value=job.licensePlate)
        ws.cell(row=row, column=3, value=job.vin)
        ws.cell(row=row, column=4, value=job.status.value if job.status else '')
        ws.cell(row=row, column=5, value=job.towReason)
        ws.cell(row=row, column=6, value=job.locationAddress)
        ws.cell(row=row, column=7, value=job.authority.name if job.authority else '')
        ws.cell(row=row, column=8, value=job.towingCompany.companyName if job.towingCompany else '')
        ws.cell(row=row, column=9, value=job.createdAt.isoformat() if job.createdAt else '')
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=auftraege.xlsx"}
    )

@api_router.get("/jobs/export/excel")
async def export_jobs_excel_alt(user = Depends(get_current_user)):
    """Alternative endpoint for Excel export"""
    return await export_jobs_excel(user)

# ============================================================================
# PDF GENERATION
# ============================================================================

@api_router.get("/jobs/{job_id}/pdf")
async def generate_job_pdf(job_id: str, user = Depends(get_current_user)):
    """Generate PDF for a job"""
    job = await prisma.towingjob.find_unique(
        where={'id': job_id},
        include={
            'authority': True,
            'towingCompany': {'include': {'pricing': True}},
            'createdByUser': {'include': {'user': True}}
        }
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)
    elements.append(Paragraph("Abschleppauftrag", title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Job info table
    data = [
        ["Auftragsnummer:", job.jobNumber],
        ["Kennzeichen:", job.licensePlate or "-"],
        ["FIN:", job.vin or "-"],
        ["Status:", safe_enum_value(job.status, "-")],
        ["Abschleppgrund:", job.towReason],
        ["Standort:", job.locationAddress],
        ["Erstellt am:", job.createdAt.strftime("%d.%m.%Y %H:%M") if job.createdAt else "-"]
    ]
    
    if job.authority:
        data.append(["Behörde:", job.authority.name])
    
    if job.towingCompany:
        data.append(["Abschleppdienst:", job.towingCompany.companyName])
    
    if job.createdByUser and job.createdByUser.user:
        data.append(["Erstellt von:", f"{job.createdByUser.user.name} ({job.createdByUser.dienstnummer})"])
    
    table = Table(data, colWidths=[5*cm, 10*cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=auftrag_{job.jobNumber}.pdf"}
    )

# PDF Token for secure download
pdf_tokens: Dict[str, dict] = {}

@api_router.get("/jobs/{job_id}/pdf/token")
async def get_pdf_token(job_id: str, user = Depends(get_current_user)):
    """Generate a temporary token for PDF download"""
    job = await prisma.towingjob.find_unique(where={'id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    # Generate token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    pdf_tokens[token] = {
        'job_id': job_id,
        'user_id': user.id,
        'expires': expiry
    }
    
    # Clean up old tokens
    current = datetime.now(timezone.utc)
    expired = [t for t, d in pdf_tokens.items() if d['expires'] < current]
    for t in expired:
        pdf_tokens.pop(t, None)
    
    return {"token": token}

# ============================================================================
# ADDITIONAL ENDPOINTS FOR FRONTEND COMPATIBILITY
# ============================================================================

@api_router.patch("/jobs/{job_id}")
async def patch_job(job_id: str, data: dict, user = Depends(get_current_user)):
    """Patch job - alternate to PUT for compatibility"""
    job = await prisma.towingjob.find_unique(where={'id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    update_data = {}
    
    # Status update
    if 'status' in data:
        status_map = {
            'pending': JobStatus.PENDING,
            'assigned': JobStatus.ASSIGNED,
            'on_site': JobStatus.ON_SITE,
            'towed': JobStatus.TOWED,
            'in_yard': JobStatus.IN_YARD,
            'released': JobStatus.RELEASED,
            'cancelled': JobStatus.CANCELLED
        }
        new_status = status_map.get(data['status'].lower())
        if new_status:
            update_data['status'] = new_status
            now = datetime.now(timezone.utc)
            if new_status == JobStatus.ASSIGNED and not job.assignedAt:
                update_data['assignedAt'] = now
                update_data['acceptedAt'] = now
            elif new_status == JobStatus.ON_SITE and not job.onSiteAt:
                update_data['onSiteAt'] = now
            elif new_status == JobStatus.TOWED and not job.towedAt:
                update_data['towedAt'] = now
            elif new_status == JobStatus.IN_YARD and not job.inYardAt:
                update_data['inYardAt'] = now
            elif new_status == JobStatus.RELEASED and not job.releasedAt:
                update_data['releasedAt'] = now
    
    # Other updates
    if 'service_notes' in data:
        update_data['serviceNotes'] = data['service_notes']
    if 'notes' in data:
        update_data['authorityNotes'] = data['notes']
    if 'owner_first_name' in data:
        update_data['ownerFirstName'] = data['owner_first_name']
    if 'owner_last_name' in data:
        update_data['ownerLastName'] = data['owner_last_name']
    if 'owner_address' in data:
        update_data['ownerStreet'] = data['owner_address']
    if 'payment_method' in data:
        payment_map = {'cash': PaymentMethod.CASH, 'card': PaymentMethod.CARD, 'invoice': PaymentMethod.INVOICE}
        pm = payment_map.get(data['payment_method'].lower() if data['payment_method'] else None)
        if pm:
            update_data['paymentMethod'] = pm
    if 'payment_amount' in data:
        update_data['paymentAmount'] = data['payment_amount']
    if 'is_empty_trip' in data:
        update_data['isEmptyTrip'] = data['is_empty_trip']
    if 'calculated_costs' in data:
        update_data['calculatedCosts'] = json.dumps(data['calculated_costs']) if data['calculated_costs'] else None
    
    updated_job = await prisma.towingjob.update(
        where={'id': job_id},
        data=update_data,
        include={
            'authority': True,
            'towingCompany': {'include': {'pricing': True}},
            'photos': True
        }
    )
    
    await log_audit("JOB_STATUS_CHANGED", user.id, user.name, user.email, "job", job_id, {
        "new_status": data.get('status')
    })
    
    # Return full job data
    return {
        'id': updated_job.id,
        'job_number': updated_job.jobNumber,
        'license_plate': updated_job.licensePlate,
        'vin': updated_job.vin,
        'tow_reason': updated_job.towReason,
        'location_address': updated_job.locationAddress,
        'location_lat': updated_job.locationLat,
        'location_lng': updated_job.locationLng,
        'status': safe_enum_value(updated_job.status),
        'job_type': safe_enum_value(updated_job.jobType, 'towing'),
        'authority_notes': updated_job.authorityNotes,
        'service_notes': updated_job.serviceNotes,
        'notes': updated_job.authorityNotes,
        'created_at': updated_job.createdAt.isoformat() if updated_job.createdAt else None,
        'updated_at': updated_job.updatedAt.isoformat() if updated_job.updatedAt else None,
        'in_yard_at': updated_job.inYardAt.isoformat() if updated_job.inYardAt else None,
        'released_at': updated_job.releasedAt.isoformat() if updated_job.releasedAt else None,
        'is_empty_trip': updated_job.isEmptyTrip,
        'owner_first_name': updated_job.ownerFirstName,
        'owner_last_name': updated_job.ownerLastName,
        'owner_address': updated_job.ownerStreet,
        'payment_method': safe_enum_value(updated_job.paymentMethod) if updated_job.paymentMethod else None,
        'payment_amount': updated_job.paymentAmount,
        'calculated_costs': updated_job.calculatedCosts,
        'authority_id': updated_job.authorityId,
        'assigned_service_id': updated_job.towingCompanyId,
        'created_by_authority': updated_job.authority.name if updated_job.authority else None,
        'assigned_service_name': updated_job.towingCompany.companyName if updated_job.towingCompany else None
    }

@api_router.post("/jobs/{job_id}/assign/{service_id}")
async def assign_job(job_id: str, service_id: str, user = Depends(get_current_user)):
    """Assign a job to a towing service"""
    job = await prisma.towingjob.find_unique(where={'id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    service = await prisma.towingcompany.find_unique(where={'id': service_id})
    if not service:
        raise HTTPException(status_code=404, detail="Abschleppdienst nicht gefunden")
    
    updated = await prisma.towingjob.update(
        where={'id': job_id},
        data={
            'towingCompanyId': service_id,
            'status': JobStatus.ASSIGNED,
            'assignedAt': datetime.now(timezone.utc)
        }
    )
    
    await log_audit("JOB_ASSIGNED", user.id, user.name, user.email, "job", job_id, {
        "service_id": service_id
    })
    
    return {"message": "Auftrag zugewiesen", "status": safe_enum_value(updated.status)}

@api_router.patch("/services/costs")
async def update_service_costs(data: dict, user = Depends(get_current_user)):
    """Update towing service costs"""
    if user.role != UserRole.TOWING_COMPANY_USER or not user.towingCompanyUser:
        raise HTTPException(status_code=403, detail="Nur für Abschleppdienste")
    
    update_data = {}
    if 'tow_cost' in data:
        update_data['towCost'] = data['tow_cost']
    if 'daily_cost' in data:
        update_data['dailyCost'] = data['daily_cost']
    if 'processing_fee' in data:
        update_data['processingFee'] = data['processing_fee']
    if 'empty_trip_fee' in data:
        update_data['emptyTripFee'] = data['empty_trip_fee']
    
    await prisma.towingcompanypricing.update(
        where={'towingCompanyId': user.towingCompanyUser.towingCompanyId},
        data=update_data
    )
    
    return {"message": "Kosten aktualisiert"}

@api_router.patch("/towing/company-info")
async def update_company_info(data: dict, user = Depends(get_current_user)):
    """Update towing company info"""
    if user.role != UserRole.TOWING_COMPANY_USER or not user.towingCompanyUser:
        raise HTTPException(status_code=403, detail="Nur für Abschleppdienste")
    
    update_data = {}
    if 'company_name' in data:
        update_data['companyName'] = data['company_name']
    if 'phone' in data:
        update_data['phone'] = data['phone']
    if 'address' in data:
        update_data['street'] = data['address']
    if 'yard_address' in data:
        update_data['yardStreet'] = data['yard_address']
    if 'yard_lat' in data:
        update_data['yardLat'] = data['yard_lat']
    if 'yard_lng' in data:
        update_data['yardLng'] = data['yard_lng']
    if 'opening_hours' in data:
        update_data['openingHours'] = data['opening_hours']
    if 'email' in data:
        update_data['email'] = data['email']
    
    await prisma.towingcompany.update(
        where={'id': user.towingCompanyUser.towingCompanyId},
        data=update_data
    )
    
    return {"message": "Firmendaten aktualisiert"}

@api_router.patch("/admin/users/{user_id}/password")
async def admin_reset_password(user_id: str, data: dict, admin = Depends(require_admin)):
    """Admin reset user password"""
    new_password = data.get('new_password')
    if not new_password:
        raise HTTPException(status_code=400, detail="Neues Passwort erforderlich")
    
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    await prisma.user.update(
        where={'id': user_id},
        data={'passwordHash': hash_password(new_password)}
    )
    
    await log_audit("PASSWORD_RESET", admin.id, admin.name, admin.email, "user", user_id)
    
    return {"message": "Passwort zurückgesetzt"}

@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin = Depends(require_admin)):
    """Admin delete user"""
    target = await prisma.user.find_unique(where={'id': user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    
    # Delete related data
    if target.role == UserRole.AUTHORITY_USER:
        auth_user = await prisma.authorityuser.find_first(where={'userId': user_id})
        if auth_user:
            await prisma.authorityuser.delete(where={'id': auth_user.id})
    elif target.role == UserRole.TOWING_COMPANY_USER:
        tc_user = await prisma.towingcompanyuser.find_first(where={'userId': user_id})
        if tc_user:
            await prisma.towingcompanyuser.delete(where={'id': tc_user.id})
    
    await prisma.user.delete(where={'id': user_id})
    
    await log_audit("USER_BLOCKED", admin.id, admin.name, admin.email, "user", user_id, {"action": "USER_DELETED"})
    
    return {"message": "Benutzer gelöscht"}

@api_router.patch("/authority/employees/{employee_id}/password")
async def reset_employee_password(employee_id: str, data: dict, user = Depends(get_current_user)):
    """Reset employee password"""
    if user.role != UserRole.AUTHORITY_USER or not user.authorityUser:
        raise HTTPException(status_code=403, detail="Nur für Behörden")
    
    if not user.authorityUser.isMainAccount:
        raise HTTPException(status_code=403, detail="Nur Haupt-Accounts können Passwörter zurücksetzen")
    
    new_password = data.get('new_password')
    if not new_password:
        raise HTTPException(status_code=400, detail="Neues Passwort erforderlich")
    
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    await prisma.user.update(
        where={'id': employee_id},
        data={'passwordHash': hash_password(new_password)}
    )
    
    return {"message": "Passwort zurückgesetzt"}

@api_router.post("/jobs/bulk-update-status")
async def bulk_update_status(data: dict, user = Depends(get_current_user)):
    """Bulk update job status"""
    job_ids = data.get('job_ids', [])
    new_status = data.get('status')
    
    if not job_ids or not new_status:
        raise HTTPException(status_code=400, detail="job_ids und status erforderlich")
    
    status_map = {
        'pending': JobStatus.PENDING,
        'assigned': JobStatus.ASSIGNED,
        'on_site': JobStatus.ON_SITE,
        'towed': JobStatus.TOWED,
        'in_yard': JobStatus.IN_YARD,
        'released': JobStatus.RELEASED
    }
    
    pg_status = status_map.get(new_status.lower())
    if not pg_status:
        raise HTTPException(status_code=400, detail="Ungültiger Status")
    
    updated_count = await prisma.towingjob.update_many(
        where={'id': {'in': job_ids}},
        data={'status': pg_status}
    )
    
    return {"message": f"{updated_count} Aufträge aktualisiert"}

@api_router.get("/auth/verify-reset-token/{token}")
async def verify_reset_token(token: str):
    """Verify password reset token"""
    token_record = await prisma.passwordresettoken.find_first(
        where={
            'token': token,
            'usedAt': None,
            'expiresAt': {'gt': datetime.now(timezone.utc)}
        }
    )
    
    if not token_record:
        raise HTTPException(status_code=400, detail="Token ungültig oder abgelaufen")
    
    return {"valid": True}

# ============================================================================
# APP CONFIGURATION
# ============================================================================

app.include_router(api_router)

_allowed_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
if "http://localhost:3000" not in _allowed_origins:
    _allowed_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Connect to database and start scheduler"""
    try:
        await prisma.connect()
        logger.info("✅ Prisma Client connected to PostgreSQL")
        
        # Start DSGVO scheduler
        scheduler.add_job(
            dsgvo_data_cleanup,
            CronTrigger(hour=3, minute=0),
            id="dsgvo_cleanup",
            name="DSGVO Daten-Anonymisierung",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"✅ DSGVO Scheduler gestartet - Retention: {DSGVO_RETENTION_DAYS} Tage")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect from database"""
    scheduler.shutdown(wait=False)
    await prisma.disconnect()
    logger.info("✅ Prisma Client disconnected")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "postgresql", "orm": "prisma"}
