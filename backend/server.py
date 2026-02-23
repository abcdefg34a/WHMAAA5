from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, validator
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
import aiofiles
import math
from collections import defaultdict
import time
from PIL import Image as PILImage
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import csv
import json
import boto3
from botocore.exceptions import ClientError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# AWS SES Configuration
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_SES_REGION = os.environ.get('AWS_SES_REGION', 'eu-central-1')
AWS_SES_VERIFIED_EMAIL = os.environ.get('AWS_SES_VERIFIED_EMAIL', 'info@werhatmeinautoabgeschleppt.de')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

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

# Rate Limiting Configuration
RATE_LIMIT_WINDOW = 900  # 15 minutes in seconds
MAX_LOGIN_ATTEMPTS = 5   # Max attempts per window
login_attempts: Dict[str, List[float]] = defaultdict(list)

# Image Compression Settings
MAX_IMAGE_SIZE = (1920, 1080)  # Max dimensions
JPEG_QUALITY = 75  # Quality for JPEG compression

# Create the main app
app = FastAPI(title="Abschlepp-Management API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ==================== STRUCTURED LOGGING ====================
def setup_logging():
    """Setup structured logging with file rotation"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Error file handler
    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=10*1024*1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    
    # Audit log handler
    audit_handler = RotatingFileHandler(
        LOG_DIR / "audit.log",
        maxBytes=10*1024*1024,
        backupCount=10
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure audit logger
    audit_logger = logging.getLogger('audit')
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    
    return logging.getLogger(__name__), audit_logger

logger, audit_logger = setup_logging()

# ==================== EMAIL SERVICE (AWS SES) ====================

class EmailService:
    """Service for sending emails via AWS SES"""
    
    def __init__(self):
        """Initialize SES client"""
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            self.ses_client = boto3.client(
                'ses',
                region_name=AWS_SES_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
            self.enabled = True
            logger.info("AWS SES Email Service initialized")
        else:
            self.ses_client = None
            self.enabled = False
            logger.warning("AWS SES not configured - emails will be logged only")
        
        self.sender_email = AWS_SES_VERIFIED_EMAIL
        self.frontend_url = FRONTEND_URL
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> Optional[str]:
        """Send email via AWS SES"""
        if not self.enabled:
            logger.info(f"[EMAIL MOCK] To: {to_email}, Subject: {subject}")
            print(f"\n{'='*60}")
            print(f"📧 EMAIL (SES nicht konfiguriert - nur Log)")
            print(f"An: {to_email}")
            print(f"Betreff: {subject}")
            print(f"{'='*60}\n")
            return None
        
        try:
            body = {
                'Html': {'Data': html_content, 'Charset': 'UTF-8'}
            }
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
            
            message_id = response['MessageId']
            logger.info(f"Email sent successfully to {to_email}, MessageId: {message_id}")
            return message_id
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to send email to {to_email}: {error_code} - {error_message}")
            
            if error_code == 'MessageRejected':
                raise Exception(f"E-Mail wurde abgelehnt: {error_message}")
            elif error_code == 'MailFromDomainNotVerified':
                raise Exception("Absender-E-Mail nicht verifiziert")
            else:
                raise Exception(f"E-Mail-Versand fehlgeschlagen: {error_message}")
    
    def send_password_reset_email(self, to_email: str, reset_token: str, user_name: str) -> Optional[str]:
        """Send password reset email"""
        reset_link = f"{self.frontend_url}/reset-password?token={reset_token}"
        
        subject = "Passwort zurücksetzen - AbschleppPortal"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 40px 30px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #1e293b; margin: 0; font-size: 24px; }}
                .logo {{ font-size: 32px; margin-bottom: 10px; }}
                .content {{ margin: 20px 0; }}
                .button {{ display: inline-block; padding: 14px 32px; background-color: #f97316; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
                .button:hover {{ background-color: #ea580c; }}
                .link-box {{ background-color: #f1f5f9; padding: 12px; border-radius: 4px; word-break: break-all; font-size: 13px; margin: 15px 0; }}
                .warning {{ background-color: #fef3c7; border: 1px solid #fcd34d; border-radius: 6px; padding: 12px; margin: 20px 0; font-size: 14px; }}
                .footer {{ font-size: 12px; color: #64748b; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚗</div>
                    <h1>Passwort zurücksetzen</h1>
                </div>
                
                <div class="content">
                    <p>Hallo {user_name},</p>
                    
                    <p>Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt. Klicken Sie auf den Button unten, um ein neues Passwort zu erstellen:</p>
                    
                    <center>
                        <a href="{reset_link}" class="button">Passwort zurücksetzen</a>
                    </center>
                    
                    <p>Oder kopieren Sie diesen Link in Ihren Browser:</p>
                    <div class="link-box">{reset_link}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Hinweis:</strong> Dieser Link ist 1 Stunde gültig. Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.
                    </div>
                </div>
                
                <div class="footer">
                    <p>Diese E-Mail wurde automatisch gesendet. Bitte antworten Sie nicht direkt darauf.</p>
                    <p>© {datetime.now().year} AbschleppPortal - werhatmeinautoabgeschleppt.de</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Passwort zurücksetzen - AbschleppPortal

Hallo {user_name},

Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.

Klicken Sie auf diesen Link, um ein neues Passwort zu erstellen:
{reset_link}

Dieser Link ist 1 Stunde gültig. Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.

Mit freundlichen Grüßen,
Ihr AbschleppPortal Team
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_registration_confirmation(self, to_email: str, user_name: str, role: str) -> Optional[str]:
        """Send registration confirmation email"""
        role_name = "Behörde" if role == "authority" else "Abschleppdienst"
        
        subject = f"Registrierung bestätigt - AbschleppPortal"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 40px 30px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #16a34a; margin: 0; font-size: 24px; }}
                .success-icon {{ font-size: 48px; margin-bottom: 15px; }}
                .content {{ margin: 20px 0; }}
                .info-box {{ background-color: #dbeafe; border: 1px solid #3b82f6; border-radius: 6px; padding: 15px; margin: 20px 0; }}
                .footer {{ font-size: 12px; color: #64748b; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">✅</div>
                    <h1>Willkommen bei AbschleppPortal!</h1>
                </div>
                
                <div class="content">
                    <p>Hallo {user_name},</p>
                    
                    <p>Vielen Dank für Ihre Registrierung als <strong>{role_name}</strong>!</p>
                    
                    <div class="info-box">
                        <strong>ℹ️ Nächste Schritte:</strong><br>
                        Ihre Registrierung muss von einem Administrator freigegeben werden, bevor Sie das Portal nutzen können. Sie erhalten eine weitere E-Mail, sobald Ihr Konto aktiviert wurde.
                    </div>
                    
                    <p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>
                </div>
                
                <div class="footer">
                    <p>© {datetime.now().year} AbschleppPortal - werhatmeinautoabgeschleppt.de</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_account_approved_email(self, to_email: str, user_name: str, role: str) -> Optional[str]:
        """Send account approval notification"""
        role_name = "Behörde" if role == "authority" else "Abschleppdienst"
        login_url = f"{self.frontend_url}/portal"
        
        subject = "Ihr Konto wurde freigeschaltet - AbschleppPortal"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 40px 30px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #16a34a; margin: 0; font-size: 24px; }}
                .success-icon {{ font-size: 48px; margin-bottom: 15px; }}
                .button {{ display: inline-block; padding: 14px 32px; background-color: #16a34a; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
                .footer {{ font-size: 12px; color: #64748b; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">🎉</div>
                    <h1>Konto freigeschaltet!</h1>
                </div>
                
                <div class="content">
                    <p>Hallo {user_name},</p>
                    
                    <p>Gute Nachrichten! Ihr Konto als <strong>{role_name}</strong> wurde von einem Administrator freigegeben.</p>
                    
                    <p>Sie können sich jetzt anmelden und das Portal nutzen:</p>
                    
                    <center>
                        <a href="{login_url}" class="button">Zum Portal anmelden</a>
                    </center>
                </div>
                
                <div class="footer">
                    <p>© {datetime.now().year} AbschleppPortal - werhatmeinautoabgeschleppt.de</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_job_notification(self, to_email: str, job_number: str, license_plate: str, status: str, service_name: str = None) -> Optional[str]:
        """Send job status notification"""
        status_labels = {
            'assigned': 'Zugewiesen',
            'on_site': 'Abschleppdienst vor Ort',
            'towed': 'Fahrzeug abgeschleppt',
            'in_yard': 'Fahrzeug im Hof',
            'released': 'Fahrzeug abgeholt'
        }
        status_label = status_labels.get(status, status)
        
        subject = f"Auftrag {job_number} - {status_label}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .container {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 40px 30px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #1e293b; margin: 0; font-size: 24px; }}
                .status-badge {{ display: inline-block; padding: 8px 16px; background-color: #f97316; color: white; border-radius: 20px; font-weight: 600; }}
                .details {{ background-color: #f1f5f9; border-radius: 6px; padding: 15px; margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e2e8f0; }}
                .footer {{ font-size: 12px; color: #64748b; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚗 Auftrags-Update</h1>
                </div>
                
                <div class="content">
                    <center>
                        <span class="status-badge">{status_label}</span>
                    </center>
                    
                    <div class="details">
                        <div class="detail-row">
                            <strong>Auftragsnummer:</strong>
                            <span>{job_number}</span>
                        </div>
                        <div class="detail-row">
                            <strong>Kennzeichen:</strong>
                            <span>{license_plate}</span>
                        </div>
                        {f'<div class="detail-row"><strong>Abschleppdienst:</strong><span>{service_name}</span></div>' if service_name else ''}
                    </div>
                </div>
                
                <div class="footer">
                    <p>© {datetime.now().year} AbschleppPortal - werhatmeinautoabgeschleppt.de</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)

# Initialize email service
email_service = EmailService()

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
    yard_lat: Optional[float] = None  # NEW: Yard coordinates
    yard_lng: Optional[float] = None  # NEW: Yard coordinates
    opening_hours: Optional[str] = None
    service_code: Optional[str] = None
    linked_services: Optional[List[str]] = None
    linked_authorities: Optional[List[str]] = None  # NEW: Authorities that linked this service
    created_at: str
    # Pricing fields
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
    # NEW: Extended pricing settings
    time_based_enabled: Optional[bool] = None
    first_half_hour: Optional[float] = None
    additional_half_hour: Optional[float] = None
    processing_fee: Optional[float] = None
    empty_trip_fee: Optional[float] = None
    night_surcharge: Optional[float] = None
    weekend_surcharge: Optional[float] = None
    heavy_vehicle_surcharge: Optional[float] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UpdateCostsRequest(BaseModel):
    tow_cost: float
    daily_cost: float

# NEW: Extended pricing settings for towing services
class PricingSettingsRequest(BaseModel):
    # Zeitbasiert
    time_based_enabled: Optional[bool] = False
    first_half_hour: Optional[float] = None
    additional_half_hour: Optional[float] = None
    # Standard
    tow_cost: Optional[float] = None
    daily_cost: Optional[float] = None
    # Zusatzkosten
    processing_fee: Optional[float] = None  # Bearbeitungsgebühr
    empty_trip_fee: Optional[float] = None  # Leerfahrt
    night_surcharge: Optional[float] = None  # Nachtzuschlag
    weekend_surcharge: Optional[float] = None  # Wochenendzuschlag
    heavy_vehicle_surcharge: Optional[float] = None  # Schwerlast ab 3,5t

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
    # NEW: For towing service creating jobs on behalf of authority
    for_authority_id: Optional[str] = None
    # NEW: Job type and Sicherstellung fields
    job_type: Optional[str] = "towing"  # "towing" or "sicherstellung"
    # Sicherstellung-specific fields
    sicherstellung_reason: Optional[str] = None
    vehicle_category: Optional[str] = None  # "under_3_5t" or "over_3_5t"
    ordering_authority: Optional[str] = None
    contact_attempts: Optional[bool] = None
    contact_attempts_notes: Optional[str] = None
    estimated_vehicle_value: Optional[float] = None

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
    # NEW: Empty trip flag
    is_empty_trip: Optional[bool] = None

# NEW: Model for editing job vehicle data (Kennzeichen, FIN, etc.)
class JobEditData(BaseModel):
    license_plate: Optional[str] = None
    vin: Optional[str] = None
    tow_reason: Optional[str] = None
    notes: Optional[str] = None
    location_address: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

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
    created_by_dienstnummer: Optional[str] = None
    authority_id: Optional[str] = None
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
    accepted_at: Optional[str] = None  # NEW: When job was accepted
    # NEW: Job type and Sicherstellung fields
    job_type: Optional[str] = "towing"
    sicherstellung_reason: Optional[str] = None
    vehicle_category: Optional[str] = None
    ordering_authority: Optional[str] = None
    contact_attempts: Optional[bool] = None
    contact_attempts_notes: Optional[str] = None
    estimated_vehicle_value: Optional[float] = None
    is_empty_trip: Optional[bool] = None
    # NEW: Calculated costs breakdown
    calculated_costs: Optional[dict] = None
    # NEW: Track if created by towing service
    created_by_service: Optional[bool] = False

class VehicleSearchResult(BaseModel):
    found: bool
    job_number: Optional[str] = None
    license_plate: Optional[str] = None
    status: Optional[str] = None
    towed_at: Optional[str] = None
    in_yard_at: Optional[str] = None
    yard_address: Optional[str] = None
    yard_lat: Optional[float] = None  # NEW: Yard coordinates for map
    yard_lng: Optional[float] = None  # NEW: Yard coordinates for map
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    opening_hours: Optional[str] = None
    # Cost calculation
    tow_cost: Optional[float] = None
    daily_cost: Optional[float] = None
    days_in_yard: Optional[int] = None
    total_cost: Optional[float] = None
    # Location coordinates for map - REMOVED, using yard coordinates instead
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    # NEW: Additional info for towed status
    tow_reason: Optional[str] = None
    location_address: Optional[str] = None
    created_by_authority: Optional[str] = None

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

def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Passwort muss mindestens 8 Zeichen lang sein"
    if not re.search(r'[A-Z]', password):
        return False, "Passwort muss mindestens einen Großbuchstaben enthalten"
    if not re.search(r'[a-z]', password):
        return False, "Passwort muss mindestens einen Kleinbuchstaben enthalten"
    if not re.search(r'\d', password):
        return False, "Passwort muss mindestens eine Zahl enthalten"
    return True, ""

def check_rate_limit(identifier: str) -> tuple[bool, int]:
    """
    Check if login attempts are within rate limit.
    Returns (is_allowed, seconds_until_reset)
    """
    current_time = time.time()
    # Clean old attempts
    login_attempts[identifier] = [
        t for t in login_attempts[identifier] 
        if current_time - t < RATE_LIMIT_WINDOW
    ]
    
    if len(login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        oldest_attempt = min(login_attempts[identifier])
        seconds_remaining = int(RATE_LIMIT_WINDOW - (current_time - oldest_attempt))
        return False, seconds_remaining
    
    return True, 0

def record_login_attempt(identifier: str):
    """Record a failed login attempt"""
    login_attempts[identifier].append(time.time())

def clear_login_attempts(identifier: str):
    """Clear login attempts after successful login"""
    login_attempts[identifier] = []

def generate_reset_token() -> str:
    """Generate a secure password reset token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))

# ==================== IMAGE COMPRESSION ====================

def compress_image_base64(base64_data: str, max_size: tuple = MAX_IMAGE_SIZE, quality: int = JPEG_QUALITY) -> str:
    """
    Compress a base64 encoded image.
    Returns compressed base64 string.
    """
    try:
        # Handle data URL format
        if ',' in base64_data:
            header, data = base64_data.split(',', 1)
        else:
            header = "data:image/jpeg;base64"
            data = base64_data
        
        # Decode base64
        image_data = base64.b64decode(data)
        
        # Open with Pillow
        img = PILImage.open(BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
        
        # Save compressed
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Encode back to base64
        compressed_data = base64.b64encode(output.read()).decode()
        
        logger.info(f"Image compressed: {len(data)} -> {len(compressed_data)} bytes ({int((1-len(compressed_data)/len(data))*100)}% reduction)")
        
        return f"data:image/jpeg;base64,{compressed_data}"
    except Exception as e:
        logger.error(f"Image compression failed: {e}")
        return base64_data  # Return original if compression fails

# ==================== AUDIT LOGGING ====================

async def log_audit(action: str, user_id: str, user_name: str, details: Dict[str, Any] = None):
    """Log an audit event to both file and database"""
    now = datetime.now(timezone.utc).isoformat()
    
    audit_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": now,
        "action": action,
        "user_id": user_id,
        "user_name": user_name,
        "details": details or {},
        "created_at": now
    }
    
    # Log to file
    audit_logger.info(json.dumps(audit_entry, ensure_ascii=False))
    
    # Log to database
    try:
        await db.audit_logs.insert_one(audit_entry)
    except Exception as e:
        logger.error(f"Failed to save audit log to DB: {e}")
    
    return audit_entry

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

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserRegister, request: Request):
    # Check if email exists
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")
    
    # Validate password strength
    is_valid, error_msg = validate_password(data.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "role": data.role,
        "name": data.name,
        "created_at": now,
        "email_verified": False  # Email verification status
    }
    
    if data.role == UserRole.AUTHORITY:
        user_doc["authority_name"] = data.authority_name
        user_doc["department"] = data.department
        user_doc["linked_services"] = []
        user_doc["is_main_authority"] = True
        user_doc["parent_authority_id"] = None
        # Generate Dienstnummer for main authority
        user_doc["dienstnummer"] = await generate_dienstnummer(user_id)
        # Authority also needs approval
        user_doc["approval_status"] = ApprovalStatus.PENDING
        user_doc["rejection_reason"] = None
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
    
    # Audit log new registration
    await log_audit("USER_REGISTERED", user_id, data.name, {
        "email": data.email,
        "role": data.role,
        "approval_required": data.role in [UserRole.TOWING_SERVICE, UserRole.AUTHORITY]
    })
    
    # Send registration confirmation email
    try:
        email_service.send_registration_confirmation(
            to_email=data.email,
            user_name=data.name,
            role=data.role
        )
        logger.info(f"Registration confirmation email sent to {data.email}")
    except Exception as e:
        logger.error(f"Failed to send registration email: {e}")
    
    # For towing services and authorities: Don't return token, they need approval first
    if data.role in [UserRole.TOWING_SERVICE, UserRole.AUTHORITY]:
        raise HTTPException(
            status_code=202,  # Accepted but not complete
            detail="Registrierung erfolgreich! Ihr Konto muss erst von einem Administrator freigeschaltet werden. Sie erhalten eine Benachrichtigung, sobald Ihr Konto aktiviert wurde."
        )
    
    # For admin and other roles: Return token immediately
    token = create_token(user_id, data.role)
    user_doc.pop("password")
    user_doc.pop("_id", None)
    
    return TokenResponse(access_token=token, user=UserResponse(**user_doc))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request):
    # Get client IP for rate limiting
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
    
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        # Record failed attempt
        record_login_attempt(rate_limit_key)
        attempts_left = MAX_LOGIN_ATTEMPTS - len(login_attempts[rate_limit_key])
        # Audit log failed login attempt
        await log_audit("LOGIN_FAILED", "unknown", data.email, {
            "email": data.email,
            "ip_address": client_ip,
            "reason": "invalid_credentials"
        })
        raise HTTPException(
            status_code=401, 
            detail=f"Ungültige Anmeldedaten. Noch {attempts_left} Versuche übrig."
        )
    
    # Check if user is blocked
    if user.get("is_blocked"):
        raise HTTPException(status_code=403, detail="Ihr Konto wurde gesperrt. Bitte kontaktieren Sie den Administrator.")
    
    # Check if authority or towing service is approved (employees don't need approval)
    if user["role"] in [UserRole.TOWING_SERVICE, UserRole.AUTHORITY]:
        # Skip approval check for employee accounts (they inherit from parent)
        if user.get("is_main_authority") == False and user.get("parent_authority_id"):
            pass  # Employee accounts don't need separate approval
        elif user["role"] == UserRole.AUTHORITY and not user.get("is_main_authority"):
            pass  # Non-main authority employees
        else:
            # Main accounts need approval
            approval_status = user.get("approval_status")
            if approval_status is None or approval_status == ApprovalStatus.PENDING:
                raise HTTPException(status_code=403, detail="Ihr Konto wartet noch auf Freischaltung durch einen Administrator")
            elif approval_status == ApprovalStatus.REJECTED:
                rejection_reason = user.get("rejection_reason", "")
                raise HTTPException(status_code=403, detail=f"Ihre Registrierung wurde abgelehnt: {rejection_reason}. Sie können sich erneut registrieren.")
    
    # Clear rate limit on successful login
    clear_login_attempts(rate_limit_key)
    
    # Audit log successful login
    await log_audit("USER_LOGIN", user["id"], user.get("name", user["email"]), {
        "email": user["email"],
        "role": user["role"],
        "ip_address": client_ip
    })
    
    token = create_token(user["id"], user["role"])
    user.pop("password")
    user.pop("_id", None)
    
    return TokenResponse(access_token=token, user=UserResponse(**user))

# ==================== PASSWORD RESET ====================

@api_router.post("/auth/forgot-password")
async def forgot_password(data: PasswordResetRequest):
    """Request password reset - sends email with reset link"""
    user = await db.users.find_one({"email": data.email})
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "Falls ein Konto mit dieser E-Mail existiert, erhalten Sie einen Link zum Zurücksetzen."}
    
    # Generate reset token
    reset_token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Store reset token in database
    await db.password_resets.delete_many({"user_id": user["id"]})  # Remove old tokens
    await db.password_resets.insert_one({
        "user_id": user["id"],
        "email": user["email"],
        "token": reset_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Send password reset email via AWS SES
    try:
        email_service.send_password_reset_email(
            to_email=user["email"],
            reset_token=reset_token,
            user_name=user.get("name", user["email"])
        )
        logger.info(f"Password reset email sent to {data.email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        # Still return success to prevent email enumeration
    
    return {"message": "Falls ein Konto mit dieser E-Mail existiert, erhalten Sie einen Link zum Zurücksetzen."}

@api_router.post("/auth/reset-password")
async def reset_password(data: PasswordResetConfirm):
    """Reset password using token from email"""
    # Find valid reset token
    reset_record = await db.password_resets.find_one({"token": data.token})
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link")
    
    # Check if token expired
    expires_at = datetime.fromisoformat(reset_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        await db.password_resets.delete_one({"token": data.token})
        raise HTTPException(status_code=400, detail="Der Link ist abgelaufen. Bitte fordern Sie einen neuen an.")
    
    # Validate new password
    is_valid, error_msg = validate_password(data.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Update password
    new_hashed = hash_password(data.new_password)
    await db.users.update_one(
        {"id": reset_record["user_id"]},
        {"$set": {"password": new_hashed}}
    )
    
    # Audit log password reset
    await log_audit("PASSWORD_RESET", reset_record["user_id"], reset_record["email"], {
        "email": reset_record["email"],
        "method": "reset_token"
    })
    
    # Delete used token
    await db.password_resets.delete_one({"token": data.token})
    
    return {"message": "Passwort erfolgreich geändert. Sie können sich jetzt anmelden."}

@api_router.get("/auth/verify-reset-token/{token}")
async def verify_reset_token(token: str):
    """Verify if a reset token is valid"""
    reset_record = await db.password_resets.find_one({"token": token})
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Ungültiger Link")
    
    expires_at = datetime.fromisoformat(reset_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Der Link ist abgelaufen")
    
    return {"valid": True, "email": reset_record["email"]}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(**user)

# ==================== TOWING SERVICE ROUTES ====================

@api_router.get("/services", response_model=List[UserResponse])
async def get_towing_services(user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.AUTHORITY:
        # For employees, get linked services from the main authority account
        if user.get("is_main_authority"):
            linked_ids = user.get("linked_services", [])
        else:
            # Employee - get linked services from parent authority
            parent = await db.users.find_one({"id": user.get("parent_authority_id")})
            linked_ids = parent.get("linked_services", []) if parent else []
        
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
    
    # Only main authority can link services
    if not user.get("is_main_authority"):
        raise HTTPException(status_code=403, detail="Nur der Haupt-Account kann Abschleppdienste verknüpfen")
    
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
    
    # Add service to authority's linked_services
    await db.users.update_one(
        {"id": user["id"]},
        {"$push": {"linked_services": service["id"]}}
    )
    
    # NEW: Also add authority to service's linked_authorities (bidirectional link)
    await db.users.update_one(
        {"id": service["id"]},
        {"$addToSet": {"linked_authorities": user["id"]}}
    )
    
    return {"message": "Service linked successfully", "service_name": service["company_name"]}

@api_router.delete("/services/unlink/{service_id}")
async def unlink_service(service_id: str, user: dict = Depends(get_current_user)):
    if user["role"] != UserRole.AUTHORITY:
        raise HTTPException(status_code=403, detail="Only authorities can unlink services")
    
    # Only main authority can unlink services
    if not user.get("is_main_authority"):
        raise HTTPException(status_code=403, detail="Nur der Haupt-Account kann Abschleppdienste entfernen")
    
    # Remove service from authority's linked_services
    await db.users.update_one(
        {"id": user["id"]},
        {"$pull": {"linked_services": service_id}}
    )
    
    # NEW: Also remove authority from service's linked_authorities
    await db.users.update_one(
        {"id": service_id},
        {"$pull": {"linked_authorities": user["id"]}}
    )
    
    return {"message": "Service unlinked successfully"}

# NEW: Get linked authorities for towing service
@api_router.get("/towing/linked-authorities")
async def get_linked_authorities(user: dict = Depends(get_current_user)):
    """Get all authorities that have linked this towing service"""
    if user["role"] != UserRole.TOWING_SERVICE:
        raise HTTPException(status_code=403, detail="Nur Abschleppdienste können ihre verknüpften Behörden abrufen")
    
    linked_authority_ids = user.get("linked_authorities", [])
    if not linked_authority_ids:
        return []
    
    # Fetch authority details
    authorities = await db.users.find(
        {
            "id": {"$in": linked_authority_ids}, 
            "role": UserRole.AUTHORITY,
            "is_main_authority": True,
            "approval_status": ApprovalStatus.APPROVED
        },
        {"_id": 0, "password": 0, "business_license": 0}
    ).to_list(length=100)
    
    return [UserResponse(**a) for a in authorities]

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

# NEW: Extended pricing settings endpoint
@api_router.patch("/services/pricing-settings")
async def update_pricing_settings(data: PricingSettingsRequest, user: dict = Depends(get_current_user)):
    """Update extended pricing settings for towing service"""
    if user["role"] != UserRole.TOWING_SERVICE:
        raise HTTPException(status_code=403, detail="Only towing services can update pricing")
    
    update_data = {}
    if data.time_based_enabled is not None:
        update_data["time_based_enabled"] = data.time_based_enabled
    if data.first_half_hour is not None:
        update_data["first_half_hour"] = data.first_half_hour
    if data.additional_half_hour is not None:
        update_data["additional_half_hour"] = data.additional_half_hour
    if data.tow_cost is not None:
        update_data["tow_cost"] = data.tow_cost
    if data.daily_cost is not None:
        update_data["daily_cost"] = data.daily_cost
    if data.processing_fee is not None:
        update_data["processing_fee"] = data.processing_fee
    if data.empty_trip_fee is not None:
        update_data["empty_trip_fee"] = data.empty_trip_fee
    if data.night_surcharge is not None:
        update_data["night_surcharge"] = data.night_surcharge
    if data.weekend_surcharge is not None:
        update_data["weekend_surcharge"] = data.weekend_surcharge
    if data.heavy_vehicle_surcharge is not None:
        update_data["heavy_vehicle_surcharge"] = data.heavy_vehicle_surcharge
    
    if update_data:
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    
    # Audit log
    await log_audit("PRICING_UPDATED", user["id"], user.get("company_name", user["name"]), {
        "settings": update_data
    })
    
    return UserResponse(**updated_user)

# NEW: Update company info (address, phone, email, opening hours)
class CompanyInfoUpdate(BaseModel):
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    yard_address: Optional[str] = None
    yard_lat: Optional[float] = None
    yard_lng: Optional[float] = None
    opening_hours: Optional[str] = None

@api_router.patch("/towing/company-info")
async def update_company_info(data: CompanyInfoUpdate, user: dict = Depends(get_current_user)):
    """Update towing service company information"""
    if user["role"] != UserRole.TOWING_SERVICE:
        raise HTTPException(status_code=403, detail="Nur Abschleppdienste können Firmendaten ändern")
    
    update_data = {}
    if data.company_name is not None:
        update_data["company_name"] = data.company_name
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.email is not None:
        update_data["email"] = data.email
    if data.yard_address is not None:
        update_data["yard_address"] = data.yard_address
    if data.yard_lat is not None:
        update_data["yard_lat"] = data.yard_lat
    if data.yard_lng is not None:
        update_data["yard_lng"] = data.yard_lng
    if data.opening_hours is not None:
        update_data["opening_hours"] = data.opening_hours
    
    if update_data:
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    
    # Audit log
    await log_audit("COMPANY_INFO_UPDATED", user["id"], user.get("company_name", user["name"]), {
        "updated_fields": list(update_data.keys())
    })
    
    return UserResponse(**updated_user)

# NEW: Calculate job costs based on service pricing
@api_router.get("/jobs/{job_id}/calculate-costs")
async def calculate_job_costs(job_id: str, user: dict = Depends(get_current_user)):
    """Calculate costs for a job based on the towing service's pricing settings"""
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    service = await db.users.find_one({"id": job.get("assigned_service_id")})
    if not service:
        return {"total": 0, "breakdown": []}
    
    breakdown = []
    total = 0.0
    
    # Check if time-based pricing is enabled
    if service.get("time_based_enabled") and job.get("accepted_at") and job.get("in_yard_at"):
        accepted = datetime.fromisoformat(job["accepted_at"].replace("Z", "+00:00"))
        in_yard = datetime.fromisoformat(job["in_yard_at"].replace("Z", "+00:00"))
        duration_minutes = (in_yard - accepted).total_seconds() / 60
        half_hours = max(1, int((duration_minutes + 29) / 30))  # Round up
        
        first_hh = service.get("first_half_hour", 0) or 0
        add_hh = service.get("additional_half_hour", 0) or 0
        
        if first_hh > 0:
            breakdown.append({"label": "Erste halbe Stunde", "amount": first_hh})
            total += first_hh
        
        if half_hours > 1 and add_hh > 0:
            additional = (half_hours - 1) * add_hh
            breakdown.append({"label": f"{half_hours - 1} × weitere halbe Stunde", "amount": additional})
            total += additional
    else:
        # Standard pricing
        tow_cost = service.get("tow_cost", 0) or 0
        if tow_cost > 0:
            breakdown.append({"label": "Anfahrt/Abschleppen", "amount": tow_cost})
            total += tow_cost
    
    # Daily costs (if in yard)
    if job.get("in_yard_at"):
        daily_cost = service.get("daily_cost", 0) or 0
        if daily_cost > 0:
            in_yard_date = datetime.fromisoformat(job["in_yard_at"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = max(1, (now - in_yard_date).days + 1)
            daily_total = days * daily_cost
            breakdown.append({"label": f"Standkosten ({days} Tag{'e' if days > 1 else ''})", "amount": daily_total})
            total += daily_total
    
    # Processing fee
    processing_fee = service.get("processing_fee", 0) or 0
    if processing_fee > 0:
        breakdown.append({"label": "Bearbeitungsgebühr", "amount": processing_fee})
        total += processing_fee
    
    # Empty trip fee
    if job.get("is_empty_trip"):
        empty_fee = service.get("empty_trip_fee", 0) or 0
        if empty_fee > 0:
            breakdown.append({"label": "Leerfahrt", "amount": empty_fee})
            total += empty_fee
    
    # Heavy vehicle surcharge
    if job.get("vehicle_category") == "over_3_5t":
        heavy_surcharge = service.get("heavy_vehicle_surcharge", 0) or 0
        if heavy_surcharge > 0:
            breakdown.append({"label": "Schwerlastzuschlag (ab 3,5t)", "amount": heavy_surcharge})
            total += heavy_surcharge
    
    # Night surcharge (check if towed at night: 22:00 - 06:00)
    if job.get("towed_at"):
        towed_time = datetime.fromisoformat(job["towed_at"].replace("Z", "+00:00"))
        hour = towed_time.hour
        if hour >= 22 or hour < 6:
            night_surcharge = service.get("night_surcharge", 0) or 0
            if night_surcharge > 0:
                breakdown.append({"label": "Nachtzuschlag", "amount": night_surcharge})
                total += night_surcharge
    
    # Weekend surcharge (Saturday/Sunday)
    if job.get("towed_at"):
        towed_time = datetime.fromisoformat(job["towed_at"].replace("Z", "+00:00"))
        if towed_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            weekend_surcharge = service.get("weekend_surcharge", 0) or 0
            if weekend_surcharge > 0:
                breakdown.append({"label": "Wochenendzuschlag", "amount": weekend_surcharge})
                total += weekend_surcharge
    
    return {"total": round(total, 2), "breakdown": breakdown}

# ==================== AUTHORITY EMPLOYEE MANAGEMENT ====================

def get_authority_id(user: dict) -> str:
    """Get the main authority ID for a user (either main authority or employee)"""
    if user.get("is_main_authority"):
        return user["id"]
    return user.get("parent_authority_id", user["id"])

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
    
    # Audit log employee creation
    await log_audit("EMPLOYEE_CREATED", user["id"], user["name"], {
        "employee_id": employee_id,
        "employee_email": data.email,
        "employee_name": data.name,
        "dienstnummer": dienstnummer,
        "authority_id": user["id"]
    })
    
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
    
    # Audit log employee block/unblock
    await log_audit("EMPLOYEE_BLOCKED" if data.blocked else "EMPLOYEE_UNBLOCKED", user["id"], user["name"], {
        "employee_id": employee_id,
        "employee_name": employee["name"],
        "blocked": data.blocked
    })
    
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
    
    # Audit log employee deletion
    await log_audit("EMPLOYEE_DELETED", user["id"], user["name"], {
        "employee_id": employee_id,
        "employee_name": employee["name"],
        "employee_email": employee.get("email")
    })
    
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
    
    # Audit log employee password change
    await log_audit("EMPLOYEE_PASSWORD_CHANGED", user["id"], user["name"], {
        "employee_id": employee_id,
        "employee_name": employee["name"]
    })
    
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

@api_router.get("/admin/pending-authorities", response_model=List[UserResponse])
async def get_pending_authorities(user: dict = Depends(get_current_user)):
    """Get all authorities waiting for approval"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    authorities = await db.users.find(
        {"role": UserRole.AUTHORITY, "approval_status": ApprovalStatus.PENDING, "is_main_authority": True},
        {"_id": 0, "password": 0}
    ).to_list(100)
    return [UserResponse(**a) for a in authorities]

# NEW: Sync authority-service links (ensures bidirectional linking)
@api_router.post("/admin/sync-links")
async def sync_authority_service_links(user: dict = Depends(get_current_user)):
    """Synchronize bidirectional links between authorities and towing services"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Find all authorities with linked services
    authorities = await db.users.find(
        {"role": UserRole.AUTHORITY, "linked_services": {"$exists": True, "$ne": []}},
        {"_id": 0}
    ).to_list(1000)
    
    updated_count = 0
    for auth in authorities:
        linked_services = auth.get("linked_services", [])
        for service_id in linked_services:
            # Add authority to service's linked_authorities
            result = await db.users.update_one(
                {"id": service_id, "role": UserRole.TOWING_SERVICE},
                {"$addToSet": {"linked_authorities": auth["id"]}}
            )
            if result.modified_count > 0:
                updated_count += 1
    
    await log_audit("LINKS_SYNCHRONIZED", user["id"], user["name"], {
        "updated_count": updated_count
    })
    
    return {"message": f"Synchronisierung abgeschlossen. {updated_count} Verknüpfungen aktualisiert."}

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
        # Audit log approval
        await log_audit("SERVICE_APPROVED", user["id"], user["name"], {
            "service_id": service_id,
            "company_name": service["company_name"]
        })
        
        # Send approval email
        try:
            email_service.send_account_approved_email(
                to_email=service["email"],
                user_name=service.get("name", service["company_name"]),
                role=UserRole.TOWING_SERVICE
            )
            logger.info(f"Approval email sent to {service['email']}")
        except Exception as e:
            logger.error(f"Failed to send approval email: {e}")
        
        return {"message": f"{service['company_name']} wurde freigeschaltet"}
    else:
        await db.users.update_one(
            {"id": service_id},
            {"$set": {"approval_status": ApprovalStatus.REJECTED, "rejection_reason": data.rejection_reason}}
        )
        # Audit log rejection
        await log_audit("SERVICE_REJECTED", user["id"], user["name"], {
            "service_id": service_id,
            "company_name": service["company_name"],
            "reason": data.rejection_reason
        })
        return {"message": f"{service['company_name']} wurde abgelehnt"}

@api_router.post("/admin/approve-authority/{authority_id}")
async def approve_authority(authority_id: str, data: ApproveServiceRequest, user: dict = Depends(get_current_user)):
    """Approve or reject an authority registration"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    authority = await db.users.find_one({"id": authority_id, "role": UserRole.AUTHORITY})
    if not authority:
        raise HTTPException(status_code=404, detail="Behörde nicht gefunden")
    
    if data.approved:
        await db.users.update_one(
            {"id": authority_id},
            {"$set": {"approval_status": ApprovalStatus.APPROVED, "rejection_reason": None}}
        )
        # Audit log approval
        await log_audit("AUTHORITY_APPROVED", user["id"], user["name"], {
            "authority_id": authority_id,
            "authority_name": authority["authority_name"]
        })
        
        # Send approval email
        try:
            email_service.send_account_approved_email(
                to_email=authority["email"],
                user_name=authority.get("name", authority["authority_name"]),
                role=UserRole.AUTHORITY
            )
            logger.info(f"Authority approval email sent to {authority['email']}")
        except Exception as e:
            logger.error(f"Failed to send authority approval email: {e}")
        
        return {"message": f"{authority['authority_name']} wurde freigeschaltet"}
    else:
        await db.users.update_one(
            {"id": authority_id},
            {"$set": {"approval_status": ApprovalStatus.REJECTED, "rejection_reason": data.rejection_reason}}
        )
        # Audit log rejection
        await log_audit("AUTHORITY_REJECTED", user["id"], user["name"], {
            "authority_id": authority_id,
            "authority_name": authority["authority_name"],
            "reason": data.rejection_reason
        })
        return {"message": f"{authority['authority_name']} wurde abgelehnt"}

# ==================== JOB ROUTES ====================

@api_router.post("/jobs", response_model=JobResponse)
async def create_job(data: JobCreate, user: dict = Depends(get_current_user)):
    # Allow authorities, admins, and towing services to create jobs
    if user["role"] not in [UserRole.AUTHORITY, UserRole.ADMIN, UserRole.TOWING_SERVICE]:
        raise HTTPException(status_code=403, detail="Keine Berechtigung zum Erstellen von Aufträgen")
    
    # ========== DUPLICATE LICENSE PLATE CHECK ==========
    # Check if there's an active job with the same license plate
    # A job is considered "active" if it's not in 'released' status
    normalized_plate = data.license_plate.upper().replace(" ", "").replace("-", "")
    
    # Find any job with this license plate that is NOT released
    active_job = await db.jobs.find_one({
        "$or": [
            {"license_plate": data.license_plate.upper()},
            {"license_plate": normalized_plate},
            {"license_plate": {"$regex": f"^{re.escape(normalized_plate)}$", "$options": "i"}}
        ],
        "status": {"$ne": JobStatus.RELEASED}
    })
    
    if active_job:
        raise HTTPException(
            status_code=400, 
            detail=f"Ein Fahrzeug mit diesem Kennzeichen ({active_job['license_plate']}) ist bereits im System und wurde noch nicht freigegeben. Status: {active_job['status']}"
        )
    # ========== END DUPLICATE CHECK ==========
    
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Handle towing service creating job for an authority
    if user["role"] == UserRole.TOWING_SERVICE:
        if not data.for_authority_id:
            raise HTTPException(status_code=400, detail="Abschleppdienste müssen eine Behörde angeben")
        
        # Verify the authority is linked to this towing service
        linked_authorities = user.get("linked_authorities", [])
        if data.for_authority_id not in linked_authorities:
            raise HTTPException(status_code=403, detail="Sie können nur Aufträge für verknüpfte Behörden erstellen")
        
        # Get authority details
        authority = await db.users.find_one({"id": data.for_authority_id, "role": UserRole.AUTHORITY})
        if not authority:
            raise HTTPException(status_code=404, detail="Behörde nicht gefunden")
        
        authority_id = data.for_authority_id
        authority_name = authority.get("authority_name")
        created_by_authority = authority_name
        created_by_dienstnummer = None  # Service doesn't have Dienstnummer
        # Job is auto-assigned to this towing service
        assigned_service_id = user["id"]
        assigned_service_name = user.get("company_name")
        # For service-created jobs, start in "assigned" status (already accepted)
        initial_status = JobStatus.ASSIGNED
    else:
        # Authority or Admin creating job
        # Get assigned service name if provided
        assigned_service_name = None
        assigned_service_id = data.assigned_service_id
        if assigned_service_id:
            service = await db.users.find_one({"id": assigned_service_id})
            if service:
                assigned_service_name = service.get("company_name")
        
        # Get the authority ID (either main or from parent)
        authority_id = get_authority_id(user)
        authority_name = user.get("authority_name")
        created_by_authority = authority_name
        created_by_dienstnummer = user.get("dienstnummer")
        initial_status = JobStatus.ASSIGNED if assigned_service_id else JobStatus.PENDING
    
    # Compress photos before storing
    compressed_photos = []
    for photo in data.photos:
        if photo and photo.startswith('data:image'):
            compressed_photos.append(compress_image_base64(photo))
        else:
            compressed_photos.append(photo)
    
    job_doc = {
        "id": job_id,
        "job_number": generate_job_number(),
        "license_plate": data.license_plate.upper(),
        "vin": data.vin.upper() if data.vin else None,
        "tow_reason": data.tow_reason,
        "location_address": data.location_address,
        "location_lat": data.location_lat,
        "location_lng": data.location_lng,
        "photos": compressed_photos,
        "notes": data.notes,
        "status": initial_status,
        "created_by_id": user["id"],
        "created_by_name": user["name"],
        "created_by_authority": created_by_authority,
        "created_by_dienstnummer": created_by_dienstnummer,
        "authority_id": authority_id,
        "assigned_service_id": assigned_service_id,
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
        "released_at": None,
        "accepted_at": now if user["role"] == UserRole.TOWING_SERVICE else None,  # Auto-accepted for service-created jobs
        # NEW: Job type and Sicherstellung fields
        "job_type": data.job_type or "towing",
        "sicherstellung_reason": data.sicherstellung_reason,
        "vehicle_category": data.vehicle_category,
        "ordering_authority": data.ordering_authority,
        "contact_attempts": data.contact_attempts,
        "contact_attempts_notes": data.contact_attempts_notes,
        "estimated_vehicle_value": data.estimated_vehicle_value,
        "is_empty_trip": False,
        "calculated_costs": None,
        # NEW: Track if job was created by towing service
        "created_by_service": user["role"] == UserRole.TOWING_SERVICE
    }
    
    await db.jobs.insert_one(job_doc)
    job_doc.pop("_id", None)
    
    # Log audit
    await log_audit("JOB_CREATED", user["id"], user["name"], {
        "job_id": job_id,
        "job_number": job_doc["job_number"],
        "license_plate": job_doc["license_plate"]
    })
    
    return JobResponse(**job_doc)

@api_router.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    service_id: Optional[str] = None,  # NEW: Filter by towing service
    page: int = 1,
    limit: int = 50,
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
    
    # NEW: Filter by towing service (for authorities)
    if service_id and user["role"] == UserRole.AUTHORITY:
        query["assigned_service_id"] = service_id
    
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
    
    # Pagination
    skip = (page - 1) * limit
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [JobResponse(**j) for j in jobs]

@api_router.get("/jobs/count/total")
async def get_jobs_count(
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    service_id: Optional[str] = None,  # NEW: Filter by towing service
    user: dict = Depends(get_current_user)
):
    """Get total count of jobs for pagination"""
    query = {}
    
    # Filter by role
    if user["role"] == UserRole.AUTHORITY:
        if user.get("is_main_authority"):
            query["authority_id"] = user["id"]
        else:
            query["created_by_id"] = user["id"]
    elif user["role"] == UserRole.TOWING_SERVICE:
        query["assigned_service_id"] = user["id"]
    
    if status:
        query["status"] = status
    
    # NEW: Filter by towing service (for authorities)
    if service_id and user["role"] == UserRole.AUTHORITY:
        query["assigned_service_id"] = service_id
    
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_query
    
    if search:
        search_upper = search.upper()
        query["$or"] = [
            {"license_plate": {"$regex": search_upper, "$options": "i"}},
            {"vin": {"$regex": search_upper, "$options": "i"}},
            {"job_number": {"$regex": search_upper, "$options": "i"}}
        ]
    
    count = await db.jobs.count_documents(query)
    return {"total": count}

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
            # Set accepted_at when service first accepts the job
            if not job.get("accepted_at"):
                update_data["accepted_at"] = now
        elif data.status == JobStatus.TOWED:
            update_data["towed_at"] = now
        elif data.status == JobStatus.IN_YARD:
            update_data["in_yard_at"] = now
        elif data.status == JobStatus.RELEASED:
            update_data["released_at"] = now
    
    if data.is_empty_trip is not None:
        update_data["is_empty_trip"] = data.is_empty_trip
    
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
    
    # Audit log job update
    if data.status:
        await log_audit("JOB_STATUS_UPDATED", user["id"], user.get("name", user["email"]), {
            "job_id": job_id,
            "job_number": job.get("job_number"),
            "license_plate": job.get("license_plate"),
            "old_status": job.get("status"),
            "new_status": data.status
        })
    
    updated_job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return JobResponse(**updated_job)

# ==================== JOB DATA EDITING (Kennzeichen, FIN, etc.) ====================

@api_router.patch("/jobs/{job_id}/edit-data", response_model=JobResponse)
async def edit_job_data(job_id: str, data: JobEditData, user: dict = Depends(get_current_user)):
    """Edit job vehicle data - allows corrections to license plate, VIN, etc."""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    # Check access permissions
    has_access = False
    
    if user["role"] == UserRole.ADMIN:
        has_access = True
    elif user["role"] == UserRole.AUTHORITY:
        authority_id = get_authority_id(user)
        if job.get("authority_id") == authority_id or job["created_by_id"] == user["id"]:
            has_access = True
    elif user["role"] == UserRole.TOWING_SERVICE:
        if job["assigned_service_id"] == user["id"]:
            has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Keine Berechtigung zum Bearbeiten dieses Auftrags")
    
    # Only allow editing if job is not released
    if job["status"] == JobStatus.RELEASED:
        raise HTTPException(status_code=400, detail="Abgeschlossene Aufträge können nicht mehr bearbeitet werden")
    
    now = datetime.now(timezone.utc).isoformat()
    update_data = {"updated_at": now}
    changes = []
    
    # Update license plate if provided and different
    if data.license_plate and data.license_plate.upper() != job.get("license_plate"):
        new_plate = data.license_plate.upper()
        
        # Check if new license plate already exists in another active job
        normalized_new_plate = new_plate.replace(" ", "").replace("-", "")
        existing_job = await db.jobs.find_one({
            "id": {"$ne": job_id},  # Exclude current job
            "$or": [
                {"license_plate": new_plate},
                {"license_plate": normalized_new_plate}
            ],
            "status": {"$ne": JobStatus.RELEASED}
        })
        
        if existing_job:
            raise HTTPException(
                status_code=400, 
                detail=f"Ein Fahrzeug mit diesem Kennzeichen ({new_plate}) existiert bereits im System"
            )
        
        changes.append(f"Kennzeichen: {job.get('license_plate')} → {new_plate}")
        update_data["license_plate"] = new_plate
    
    # Update VIN if provided
    if data.vin is not None:
        new_vin = data.vin.upper() if data.vin else None
        if new_vin != job.get("vin"):
            changes.append(f"FIN: {job.get('vin') or '(leer)'} → {new_vin or '(leer)'}")
            update_data["vin"] = new_vin
    
    # Update tow reason if provided
    if data.tow_reason and data.tow_reason != job.get("tow_reason"):
        changes.append(f"Abschleppgrund: {job.get('tow_reason')} → {data.tow_reason}")
        update_data["tow_reason"] = data.tow_reason
    
    # Update notes if provided
    if data.notes is not None and data.notes != job.get("notes"):
        changes.append("Bemerkungen aktualisiert")
        update_data["notes"] = data.notes
    
    # Update location if provided
    if data.location_address and data.location_address != job.get("location_address"):
        changes.append(f"Adresse aktualisiert")
        update_data["location_address"] = data.location_address
    if data.location_lat is not None:
        update_data["location_lat"] = data.location_lat
    if data.location_lng is not None:
        update_data["location_lng"] = data.location_lng
    
    if len(update_data) <= 1:  # Only updated_at
        raise HTTPException(status_code=400, detail="Keine Änderungen vorgenommen")
    
    await db.jobs.update_one({"id": job_id}, {"$set": update_data})
    
    # Audit log the changes
    await log_audit("JOB_DATA_EDITED", user["id"], user.get("name", user["email"]), {
        "job_id": job_id,
        "job_number": job.get("job_number"),
        "changes": changes
    })
    
    updated_job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return JobResponse(**updated_job)

# ==================== DELETE JOB ====================

@api_router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(get_current_user)):
    """Delete a job - only allowed for creator before it's too far in process"""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    
    # Check access permissions - only creator or admin can delete
    has_access = False
    
    if user["role"] == UserRole.ADMIN:
        has_access = True
    elif user["role"] == UserRole.AUTHORITY:
        authority_id = get_authority_id(user)
        # Authority can delete if they created the job
        if job.get("authority_id") == authority_id or job["created_by_id"] == user["id"]:
            has_access = True
    elif user["role"] == UserRole.TOWING_SERVICE:
        # Towing service can delete if they created the job (for_authority jobs)
        if job.get("created_by_id") == user["id"]:
            has_access = True
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Keine Berechtigung zum Löschen dieses Auftrags")
    
    # Only allow deletion if job is in early stages (pending, assigned, or on_site)
    # Don't allow deletion if vehicle is already towed/in_yard/released
    allowed_delete_statuses = [JobStatus.PENDING, JobStatus.ASSIGNED, JobStatus.ON_SITE]
    if job["status"] not in allowed_delete_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Auftrag kann nicht gelöscht werden - Fahrzeug wurde bereits abgeschleppt. Status: {job['status']}"
        )
    
    # Delete the job
    await db.jobs.delete_one({"id": job_id})
    
    # Audit log the deletion
    await log_audit("JOB_DELETED", user["id"], user.get("name", user["email"]), {
        "job_id": job_id,
        "job_number": job.get("job_number"),
        "license_plate": job.get("license_plate"),
        "status_at_deletion": job["status"],
        "reason": "User requested deletion"
    })
    
    return {"message": f"Auftrag {job['job_number']} wurde gelöscht"}

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
        yard_lat=service.get("yard_lat") if service else None,  # NEW: Yard coordinates
        yard_lng=service.get("yard_lng") if service else None,  # NEW: Yard coordinates
        company_name=service.get("company_name") if service else None,
        phone=service.get("phone") if service else None,
        email=service.get("email") if service else None,
        opening_hours=service.get("opening_hours") if service else None,
        tow_cost=tow_cost,
        daily_cost=daily_cost,
        days_in_yard=days_in_yard,
        total_cost=total_cost,
        location_lat=job.get("location_lat"),  # Keep for reference where car was towed from
        location_lng=job.get("location_lng"),
        # NEW: Additional info
        tow_reason=job.get("tow_reason"),
        location_address=job.get("location_address"),
        created_by_authority=job.get("created_by_authority")
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
    page: int = 1,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {}
    if status:
        query["status"] = status
    if search:
        # Full-text search across multiple fields
        query["$or"] = [
            {"license_plate": {"$regex": search, "$options": "i"}},
            {"vin": {"$regex": search, "$options": "i"}},
            {"job_number": {"$regex": search, "$options": "i"}},
            {"tow_reason": {"$regex": search, "$options": "i"}},
            {"notes": {"$regex": search, "$options": "i"}},
            {"service_notes": {"$regex": search, "$options": "i"}},
            {"location_address": {"$regex": search, "$options": "i"}},
            {"created_by_name": {"$regex": search, "$options": "i"}},
            {"assigned_service_name": {"$regex": search, "$options": "i"}},
            {"owner_first_name": {"$regex": search, "$options": "i"}},
            {"owner_last_name": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [JobResponse(**j) for j in jobs]

@api_router.get("/admin/jobs/count")
async def get_all_jobs_count(
    status: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get total count of jobs for admin pagination"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {}
    if status:
        query["status"] = status
    if search:
        # Full-text search across multiple fields
        query["$or"] = [
            {"license_plate": {"$regex": search, "$options": "i"}},
            {"vin": {"$regex": search, "$options": "i"}},
            {"job_number": {"$regex": search, "$options": "i"}},
            {"tow_reason": {"$regex": search, "$options": "i"}},
            {"notes": {"$regex": search, "$options": "i"}},
            {"service_notes": {"$regex": search, "$options": "i"}},
            {"location_address": {"$regex": search, "$options": "i"}},
            {"created_by_name": {"$regex": search, "$options": "i"}},
            {"assigned_service_name": {"$regex": search, "$options": "i"}},
            {"owner_first_name": {"$regex": search, "$options": "i"}},
            {"owner_last_name": {"$regex": search, "$options": "i"}}
        ]
    
    count = await db.jobs.count_documents(query)
    return {"total": count}

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
    
    # Audit log password change by admin
    await log_audit("ADMIN_PASSWORD_CHANGE", user["id"], user["name"], {
        "target_user_id": user_id,
        "target_user_email": target_user.get("email"),
        "target_user_name": target_user.get("name")
    })
    
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
    
    # Audit log user block/unblock
    await log_audit("USER_BLOCKED" if data.blocked else "USER_UNBLOCKED", user["id"], user["name"], {
        "target_user_id": user_id,
        "target_user_email": target_user.get("email"),
        "target_user_name": target_user.get("name"),
        "blocked": data.blocked
    })
    
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
    
    # Audit log user deletion
    await log_audit("USER_DELETED", user["id"], user["name"], {
        "deleted_user_id": user_id,
        "deleted_user_email": target_user.get("email"),
        "deleted_user_name": user_name,
        "deleted_user_role": target_user.get("role")
    })
    
    return {"message": f"{user_name} wurde permanent gelöscht"}

# ==================== PDF GENERATION ====================

def format_datetime(dt_str):
    """Format ISO datetime string to German format"""
    if not dt_str or dt_str == '-':
        return '-'
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return dt_str[:19].replace('T', ' ')

def wrap_text(text, max_length=60):
    """Wrap long text for PDF cells"""
    if not text:
        return '-'
    text = str(text)
    if len(text) <= max_length:
        return text
    # Insert line breaks for very long text
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + " " + word) <= max_length:
            current_line = (current_line + " " + word).strip()
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return "\n".join(lines)

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
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=1.5*cm, 
        leftMargin=1.5*cm, 
        topMargin=1.5*cm, 
        bottomMargin=1.5*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle', 
        parent=styles['Heading1'], 
        fontSize=20, 
        spaceAfter=5,
        alignment=1,  # Center
        textColor=colors.HexColor('#1e293b')
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', 
        parent=styles['Normal'], 
        fontSize=11, 
        spaceAfter=20,
        alignment=1,  # Center
        textColor=colors.HexColor('#64748b')
    )
    heading_style = ParagraphStyle(
        'CustomHeading', 
        parent=styles['Heading2'], 
        fontSize=12, 
        spaceAfter=8, 
        spaceBefore=15,
        textColor=colors.HexColor('#1e293b'),
        borderPadding=(0, 0, 5, 0)
    )
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        wordWrap='CJK'
    )
    
    story = []
    
    # ===== HEADER =====
    # Check if this is an empty trip
    is_empty_trip = job.get('is_empty_trip', False)
    
    if is_empty_trip:
        story.append(Paragraph("LEERFAHRT-PROTOKOLL", title_style))
    else:
        story.append(Paragraph("ABSCHLEPPPROTOKOLL", title_style))
    story.append(Paragraph(f"Auftragsnummer: {job['job_number']}", subtitle_style))
    
    # Horizontal line
    story.append(Spacer(1, 5))
    line_table = Table([['']], colWidths=[17*cm])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#f97316')),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 10))
    
    # ===== EMPTY TRIP DETAILS (if applicable) =====
    if is_empty_trip:
        story.append(Paragraph("Leerfahrt-Details", heading_style))
        
        # Parse service notes for empty trip reason
        service_notes = job.get('service_notes', '')
        empty_trip_reason = 'Fahrzeug war nicht mehr vor Ort'
        if 'Fahrer vor Ort angetroffen' in service_notes:
            empty_trip_reason = 'Fahrer vor Ort angetroffen'
        
        empty_data = [
            [Paragraph("<b>Status</b>", cell_style), Paragraph("<b>LEERFAHRT</b>", cell_style)],
            [Paragraph("<b>Grund</b>", cell_style), Paragraph(empty_trip_reason, cell_style)],
        ]
        
        # Add driver info if present
        if job.get('owner_first_name') and job.get('owner_last_name'):
            empty_data.append([
                Paragraph("<b>Angetroffene Person</b>", cell_style), 
                Paragraph(f"{job['owner_first_name']} {job['owner_last_name']}", cell_style)
            ])
            if job.get('owner_address'):
                empty_data.append([
                    Paragraph("<b>Adresse</b>", cell_style), 
                    Paragraph(job['owner_address'], cell_style)
                ])
        
        # Payment info
        if job.get('payment_amount'):
            payment_method_labels = {'cash': 'Bar', 'card': 'Karte', 'invoice': 'Rechnung'}
            payment_method = payment_method_labels.get(job.get('payment_method', ''), job.get('payment_method', '-'))
            empty_data.append([
                Paragraph("<b>Leerfahrt-Kosten</b>", cell_style), 
                Paragraph(f"{job['payment_amount']:.2f} €", cell_style)
            ])
            empty_data.append([
                Paragraph("<b>Zahlungsart</b>", cell_style), 
                Paragraph(payment_method, cell_style)
            ])
        
        empty_table = Table(empty_data, colWidths=[5*cm, 12*cm])
        empty_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fff7ed')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fed7aa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fdba74')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(empty_table)
        story.append(Spacer(1, 15))
    
    # ===== AUFTRAGSTYP =====
    job_type = job.get('job_type', 'towing')
    job_type_label = 'Sicherstellung (Polizeilich)' if job_type == 'sicherstellung' else 'Abschleppen (Falschparker)'
    
    story.append(Paragraph("Auftragsdetails", heading_style))
    order_data = [
        [Paragraph("<b>Auftragstyp</b>", cell_style), Paragraph(f"<b>{job_type_label}</b>", cell_style)],
    ]
    
    # Sicherstellung-specific details
    if job_type == 'sicherstellung':
        # Reason mapping
        reason_labels = {
            'betriebsmittel': 'Auslaufende Betriebsmittel',
            'gestohlen': 'Gestohlenes Fahrzeug / Fahndung',
            'eigentumssicherung': 'Eigentumssicherung (wertvoll/ungesichert)',
            'technische_maengel': 'Technische Mängel / Beweissicherung',
            'strafrechtlich': 'Strafrechtliche Beschlagnahme'
        }
        sicherstellung_reason = job.get('sicherstellung_reason', '')
        reason_text = reason_labels.get(sicherstellung_reason, sicherstellung_reason or '-')
        order_data.append([
            Paragraph("<b>Grund der Sicherstellung</b>", cell_style), 
            Paragraph(reason_text, cell_style)
        ])
        
        # Vehicle category
        vehicle_cat = job.get('vehicle_category', '')
        cat_label = 'PKW/Krad bis 3,5t' if vehicle_cat == 'under_3_5t' else 'Fahrzeuge ab 3,5t' if vehicle_cat == 'over_3_5t' else '-'
        order_data.append([
            Paragraph("<b>Fahrzeugkategorie</b>", cell_style), 
            Paragraph(cat_label, cell_style)
        ])
        
        # Ordering authority
        authority_labels = {
            'schutzpolizei': 'Schutzpolizei',
            'kriminalpolizei': 'Kriminalpolizei',
            'staatsanwaltschaft': 'Staatsanwaltschaft',
            'sachverstaendiger': 'Technischer Sachverständiger'
        }
        ordering_auth = job.get('ordering_authority', '')
        auth_text = authority_labels.get(ordering_auth, ordering_auth or '-')
        order_data.append([
            Paragraph("<b>Anordnende Stelle</b>", cell_style), 
            Paragraph(auth_text, cell_style)
        ])
        
        # Contact attempts
        contact_attempts = job.get('contact_attempts')
        if contact_attempts is not None:
            contact_text = 'Ja' if contact_attempts else 'Nein'
            if contact_attempts and job.get('contact_attempts_notes'):
                contact_text += f" - {job['contact_attempts_notes']}"
            order_data.append([
                Paragraph("<b>Telefonische Kontaktversuche</b>", cell_style), 
                Paragraph(wrap_text(contact_text, 50), cell_style)
            ])
        
        # Estimated vehicle value
        if job.get('estimated_vehicle_value'):
            order_data.append([
                Paragraph("<b>Geschätzter Fahrzeugwert</b>", cell_style), 
                Paragraph(f"{job['estimated_vehicle_value']:,.2f} €", cell_style)
            ])
    
    order_table = Table(order_data, colWidths=[4.5*cm, 12.5*cm])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fef3c7') if job_type == 'sicherstellung' else colors.HexColor('#f8fafc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(order_table)
    
    # ===== FAHRZEUGDATEN =====
    story.append(Paragraph("Fahrzeugdaten", heading_style))
    vehicle_data = [
        [Paragraph("<b>Kennzeichen</b>", cell_style), Paragraph(job['license_plate'], cell_style)],
        [Paragraph("<b>FIN</b>", cell_style), Paragraph(job.get('vin') or '-', cell_style)],
        [Paragraph("<b>Abschleppgrund</b>", cell_style), Paragraph(wrap_text(job['tow_reason'], 50), cell_style)],
    ]
    if job.get('created_by_dienstnummer'):
        vehicle_data.append([
            Paragraph("<b>Erfasst von</b>", cell_style), 
            Paragraph(f"{job.get('created_by_name', '-')} ({job['created_by_dienstnummer']})", cell_style)
        ])
    
    vehicle_table = Table(vehicle_data, colWidths=[4.5*cm, 12.5*cm])
    vehicle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(vehicle_table)
    
    # ===== FUNDORT =====
    story.append(Paragraph("Fundort", heading_style))
    location_data = [
        [Paragraph("<b>Adresse</b>", cell_style), Paragraph(wrap_text(job['location_address'], 55), cell_style)],
        [Paragraph("<b>Koordinaten</b>", cell_style), Paragraph(f"{job['location_lat']:.6f}, {job['location_lng']:.6f}", cell_style)],
    ]
    location_table = Table(location_data, colWidths=[4.5*cm, 12.5*cm])
    location_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(location_table)
    
    # ===== ZEITERFASSUNG =====
    story.append(Paragraph("Zeiterfassung", heading_style))
    timeline_data = [
        [
            Paragraph("<b>Schritt</b>", cell_style), 
            Paragraph("<b>Datum & Uhrzeit</b>", cell_style),
            Paragraph("<b>Status</b>", cell_style)
        ],
        [
            Paragraph("1. Meldung erfasst", cell_style), 
            Paragraph(format_datetime(job.get('created_at')), cell_style),
            Paragraph("✓" if job.get('created_at') else "-", cell_style)
        ],
        [
            Paragraph("2. Vor Ort angekommen", cell_style), 
            Paragraph(format_datetime(job.get('on_site_at')), cell_style),
            Paragraph("✓" if job.get('on_site_at') else "-", cell_style)
        ],
        [
            Paragraph("3. Abgeschleppt", cell_style), 
            Paragraph(format_datetime(job.get('towed_at')), cell_style),
            Paragraph("✓" if job.get('towed_at') else "-", cell_style)
        ],
        [
            Paragraph("4. Im Hof eingetroffen", cell_style), 
            Paragraph(format_datetime(job.get('in_yard_at')), cell_style),
            Paragraph("✓" if job.get('in_yard_at') else "-", cell_style)
        ],
        [
            Paragraph("5. Fahrzeug abgeholt", cell_style), 
            Paragraph(format_datetime(job.get('released_at')), cell_style),
            Paragraph("✓" if job.get('released_at') else "-", cell_style)
        ],
    ]
    timeline_table = Table(timeline_data, colWidths=[6*cm, 8*cm, 3*cm])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f97316')),  # Orange header
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    story.append(timeline_table)
    
    # ===== HALTERDATEN (if released) =====
    if job.get('owner_first_name'):
        story.append(Paragraph("Halterdaten", heading_style))
        owner_data = [
            [Paragraph("<b>Name</b>", cell_style), Paragraph(f"{job.get('owner_first_name', '')} {job.get('owner_last_name', '')}", cell_style)],
            [Paragraph("<b>Adresse</b>", cell_style), Paragraph(wrap_text(job.get('owner_address', '-'), 55), cell_style)],
        ]
        owner_table = Table(owner_data, colWidths=[4.5*cm, 12.5*cm])
        owner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(owner_table)
    
    # ===== ZAHLUNGSINFORMATIONEN =====
    if job.get('payment_method'):
        story.append(Paragraph("Zahlungsinformationen", heading_style))
        payment_method_text = "Bar" if job['payment_method'] == 'cash' else "Kartenzahlung"
        payment_data = [
            [Paragraph("<b>Zahlungsart</b>", cell_style), Paragraph(payment_method_text, cell_style)],
            [Paragraph("<b>Betrag</b>", cell_style), Paragraph(f"{job.get('payment_amount', 0):.2f} €", cell_style)],
        ]
        payment_table = Table(payment_data, colWidths=[4.5*cm, 12.5*cm])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#dcfce7')),  # Green background for amount
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(payment_table)
    
    # ===== ABSCHLEPPDIENST =====
    if service:
        story.append(Paragraph("Abschleppdienst", heading_style))
        service_data = [
            [Paragraph("<b>Unternehmen</b>", cell_style), Paragraph(service.get('company_name') or '-', cell_style)],
            [Paragraph("<b>Telefon</b>", cell_style), Paragraph(service.get('phone') or '-', cell_style)],
            [Paragraph("<b>Hof-Adresse</b>", cell_style), Paragraph(wrap_text(service.get('yard_address') or '-', 55), cell_style)],
            [Paragraph("<b>Öffnungszeiten</b>", cell_style), Paragraph(service.get('opening_hours') or '-', cell_style)],
        ]
        service_table = Table(service_data, colWidths=[4.5*cm, 12.5*cm])
        service_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(service_table)
    
    # ===== BEMERKUNGEN =====
    if job.get('notes') or job.get('service_notes'):
        story.append(Paragraph("Bemerkungen", heading_style))
        notes_data = []
        if job.get('notes'):
            notes_data.append([
                Paragraph("<b>Behörde</b>", cell_style), 
                Paragraph(wrap_text(job['notes'], 55), cell_style)
            ])
        if job.get('service_notes'):
            notes_data.append([
                Paragraph("<b>Abschleppdienst</b>", cell_style), 
                Paragraph(wrap_text(job['service_notes'], 55), cell_style)
            ])
        notes_table = Table(notes_data, colWidths=[4.5*cm, 12.5*cm])
        notes_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(notes_table)
    
    # ===== FOOTER =====
    story.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1
    )
    story.append(Paragraph(f"Erstellt am: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')} UTC", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Abschleppprotokoll_{job['job_number']}.pdf"}
    )

# ==================== EXPORT ENDPOINTS ====================

@api_router.get("/export/jobs/csv")
async def export_jobs_csv(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Export jobs as CSV"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Build query
    query = {}
    if status:
        query["status"] = status
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_query
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Create CSV
    output = BytesIO()
    output.write('\ufeff'.encode('utf-8'))  # UTF-8 BOM for Excel
    
    import csv
    import io
    text_output = io.StringIO()
    
    fieldnames = [
        'Auftragsnummer', 'Kennzeichen', 'FIN', 'Abschleppgrund', 'Status',
        'Standort', 'Behörde', 'Dienstnummer', 'Abschleppdienst',
        'Erstellt am', 'Vor Ort', 'Abgeschleppt', 'Im Hof', 'Abgeholt',
        'Halter Name', 'Halter Adresse', 'Zahlungsart', 'Betrag'
    ]
    
    writer = csv.DictWriter(text_output, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    
    status_map = {
        'pending': 'Ausstehend', 'assigned': 'Zugewiesen', 'on_site': 'Vor Ort',
        'towed': 'Abgeschleppt', 'in_yard': 'Im Hof', 'released': 'Abgeholt'
    }
    
    for job in jobs:
        writer.writerow({
            'Auftragsnummer': job.get('job_number', ''),
            'Kennzeichen': job.get('license_plate', ''),
            'FIN': job.get('vin', ''),
            'Abschleppgrund': job.get('tow_reason', ''),
            'Status': status_map.get(job.get('status', ''), job.get('status', '')),
            'Standort': job.get('location_address', ''),
            'Behörde': job.get('created_by_authority', ''),
            'Dienstnummer': job.get('created_by_dienstnummer', ''),
            'Abschleppdienst': job.get('assigned_service_name', ''),
            'Erstellt am': job.get('created_at', '')[:19].replace('T', ' ') if job.get('created_at') else '',
            'Vor Ort': job.get('on_site_at', '')[:19].replace('T', ' ') if job.get('on_site_at') else '',
            'Abgeschleppt': job.get('towed_at', '')[:19].replace('T', ' ') if job.get('towed_at') else '',
            'Im Hof': job.get('in_yard_at', '')[:19].replace('T', ' ') if job.get('in_yard_at') else '',
            'Abgeholt': job.get('released_at', '')[:19].replace('T', ' ') if job.get('released_at') else '',
            'Halter Name': f"{job.get('owner_first_name', '')} {job.get('owner_last_name', '')}".strip(),
            'Halter Adresse': job.get('owner_address', ''),
            'Zahlungsart': 'Bar' if job.get('payment_method') == 'cash' else ('Karte' if job.get('payment_method') == 'card' else ''),
            'Betrag': f"{job.get('payment_amount', 0):.2f}" if job.get('payment_amount') else ''
        })
    
    await log_audit("EXPORT_CSV", user["id"], user["name"], {"count": len(jobs)})
    
    csv_content = text_output.getvalue().encode('utf-8-sig')
    
    return StreamingResponse(
        BytesIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Auftraege_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@api_router.get("/export/jobs/excel")
async def export_jobs_excel(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Export jobs as Excel"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Build query
    query = {}
    if status:
        query["status"] = status
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_query
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aufträge"
    
    # Header styling
    header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = [
        'Auftragsnummer', 'Kennzeichen', 'FIN', 'Abschleppgrund', 'Status',
        'Standort', 'Behörde', 'Dienstnummer', 'Abschleppdienst',
        'Erstellt am', 'Vor Ort', 'Abgeschleppt', 'Im Hof', 'Abgeholt',
        'Halter Name', 'Halter Adresse', 'Zahlungsart', 'Betrag'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
    
    status_map = {
        'pending': 'Ausstehend', 'assigned': 'Zugewiesen', 'on_site': 'Vor Ort',
        'towed': 'Abgeschleppt', 'in_yard': 'Im Hof', 'released': 'Abgeholt'
    }
    
    for row, job in enumerate(jobs, 2):
        data = [
            job.get('job_number', ''),
            job.get('license_plate', ''),
            job.get('vin', ''),
            job.get('tow_reason', ''),
            status_map.get(job.get('status', ''), job.get('status', '')),
            job.get('location_address', ''),
            job.get('created_by_authority', ''),
            job.get('created_by_dienstnummer', ''),
            job.get('assigned_service_name', ''),
            job.get('created_at', '')[:19].replace('T', ' ') if job.get('created_at') else '',
            job.get('on_site_at', '')[:19].replace('T', ' ') if job.get('on_site_at') else '',
            job.get('towed_at', '')[:19].replace('T', ' ') if job.get('towed_at') else '',
            job.get('in_yard_at', '')[:19].replace('T', ' ') if job.get('in_yard_at') else '',
            job.get('released_at', '')[:19].replace('T', ' ') if job.get('released_at') else '',
            f"{job.get('owner_first_name', '')} {job.get('owner_last_name', '')}".strip(),
            job.get('owner_address', ''),
            'Bar' if job.get('payment_method') == 'cash' else ('Karte' if job.get('payment_method') == 'card' else ''),
            job.get('payment_amount', 0) if job.get('payment_amount') else ''
        ]
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
    
    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 50)
    
    await log_audit("EXPORT_EXCEL", user["id"], user["name"], {"count": len(jobs)})
    
    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Auftraege_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
    )

# ==================== AUDIT LOG ENDPOINTS ====================

class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    action: str
    user_id: str
    user_name: str
    details: Dict[str, Any]

@api_router.get("/admin/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    """Get audit logs (Admin only)"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {}
    if action:
        query["action"] = {"$regex": action, "$options": "i"}
    if user_id:
        query["user_id"] = user_id
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to + "T23:59:59"
        query["timestamp"] = date_query
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    
    return [AuditLogResponse(**log) for log in logs]

@api_router.get("/admin/audit-logs/count")
async def get_audit_logs_count(user: dict = Depends(get_current_user)):
    """Get total audit log count"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    count = await db.audit_logs.count_documents({})
    return {"count": count}

# ==================== FULL-TEXT SEARCH ====================

@api_router.get("/search/jobs")
async def search_jobs_fulltext(
    q: str,
    limit: int = 50,
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    """Full-text search across all job fields"""
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="Suchbegriff muss mindestens 2 Zeichen haben")
    
    # Build search query
    search_regex = {"$regex": q, "$options": "i"}
    
    query = {
        "$or": [
            {"job_number": search_regex},
            {"license_plate": search_regex},
            {"vin": search_regex},
            {"tow_reason": search_regex},
            {"location_address": search_regex},
            {"created_by_name": search_regex},
            {"created_by_authority": search_regex},
            {"created_by_dienstnummer": search_regex},
            {"assigned_service_name": search_regex},
            {"owner_first_name": search_regex},
            {"owner_last_name": search_regex},
            {"owner_address": search_regex},
            {"notes": search_regex},
            {"service_notes": search_regex}
        ]
    }
    
    # Apply role-based filtering
    if user["role"] == UserRole.AUTHORITY:
        if user.get("is_main_authority"):
            query["authority_id"] = user["id"]
        else:
            query["created_by_id"] = user["id"]
    elif user["role"] == UserRole.TOWING_SERVICE:
        query["assigned_service_id"] = user["id"]
    
    total = await db.jobs.count_documents(query)
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "total": total,
        "results": [JobResponse(**j) for j in jobs],
        "query": q
    }

# ==================== PAGINATION FOR JOBS ====================

@api_router.get("/jobs/paginated")
async def get_jobs_paginated(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get paginated jobs with filters"""
    query = {}
    
    # Role-based filtering
    if user["role"] == UserRole.AUTHORITY:
        if user.get("is_main_authority"):
            query["authority_id"] = user["id"]
        else:
            query["created_by_id"] = user["id"]
    elif user["role"] == UserRole.TOWING_SERVICE:
        query["assigned_service_id"] = user["id"]
    
    # Apply filters
    if status:
        query["status"] = status
    
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_query
    
    if search:
        search_upper = search.upper()
        query["$or"] = [
            {"license_plate": {"$regex": search_upper, "$options": "i"}},
            {"vin": {"$regex": search_upper, "$options": "i"}},
            {"job_number": {"$regex": search_upper, "$options": "i"}}
        ]
    
    # Calculate pagination
    skip = (page - 1) * per_page
    total = await db.jobs.count_documents(query)
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)
    
    return {
        "data": [JobResponse(**j) for j in jobs],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

# ==================== DATABASE BACKUP ====================

@api_router.post("/admin/backup")
async def create_backup(user: dict = Depends(get_current_user)):
    """Create a database backup (Admin only)"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_data = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user["name"],
            "collections": {}
        }
        
        # Export collections
        collections = ["users", "jobs", "audit_logs", "password_resets"]
        for collection_name in collections:
            docs = await db[collection_name].find({}, {"_id": 0}).to_list(None)
            backup_data["collections"][collection_name] = docs
        
        # Save backup file
        backup_file = BACKUP_DIR / f"backup_{backup_time}.json"
        async with aiofiles.open(backup_file, 'w') as f:
            await f.write(json.dumps(backup_data, ensure_ascii=False, indent=2, default=str))
        
        # Log audit
        await log_audit("DATABASE_BACKUP", user["id"], user["name"], {
            "filename": f"backup_{backup_time}.json",
            "collections": collections
        })
        
        logger.info(f"Database backup created: {backup_file}")
        
        return {
            "message": "Backup erfolgreich erstellt",
            "filename": f"backup_{backup_time}.json",
            "size": backup_file.stat().st_size
        }
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup fehlgeschlagen: {str(e)}")

@api_router.get("/admin/backups")
async def list_backups(user: dict = Depends(get_current_user)):
    """List all available backups"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    backups = []
    for f in sorted(BACKUP_DIR.glob("backup_*.json"), reverse=True):
        backups.append({
            "filename": f.name,
            "size": f.stat().st_size,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    
    return backups

@api_router.get("/admin/backups/{filename}")
async def download_backup(filename: str, user: dict = Depends(get_current_user)):
    """Download a backup file"""
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    
    backup_file = BACKUP_DIR / filename
    if not backup_file.exists() or not filename.startswith("backup_"):
        raise HTTPException(status_code=404, detail="Backup nicht gefunden")
    
    return FileResponse(backup_file, filename=filename)

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

@app.on_event("startup")
async def startup_event():
    """Create database indexes for improved query performance"""
    try:
        # Indexes for jobs collection
        await db.jobs.create_index("license_plate")
        await db.jobs.create_index("status")
        await db.jobs.create_index("created_at")
        await db.jobs.create_index("authority_id")
        await db.jobs.create_index("assigned_service_id")
        await db.jobs.create_index("job_number")
        await db.jobs.create_index([("license_plate", 1), ("status", 1)])  # Compound index
        
        # Indexes for users collection
        await db.users.create_index("email", unique=True)
        await db.users.create_index("role")
        await db.users.create_index("linked_authorities")
        
        # Indexes for audit_logs collection
        await db.audit_logs.create_index("timestamp")
        await db.audit_logs.create_index("action")
        await db.audit_logs.create_index("user_id")
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
