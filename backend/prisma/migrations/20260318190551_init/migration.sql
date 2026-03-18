-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('ADMIN', 'AUTHORITY_USER', 'TOWING_COMPANY_USER');

-- CreateEnum
CREATE TYPE "ApprovalStatus" AS ENUM ('PENDING', 'APPROVED', 'REJECTED');

-- CreateEnum
CREATE TYPE "JobStatus" AS ENUM ('PENDING', 'ASSIGNED', 'ON_SITE', 'TOWED', 'IN_YARD', 'RELEASED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "JobType" AS ENUM ('TOWING', 'SICHERSTELLUNG');

-- CreateEnum
CREATE TYPE "VehicleCategory" AS ENUM ('UNDER_3_5T', 'OVER_3_5T');

-- CreateEnum
CREATE TYPE "PaymentMethod" AS ENUM ('CASH', 'CARD', 'INVOICE', 'BANK_TRANSFER');

-- CreateEnum
CREATE TYPE "PhotoType" AS ENUM ('AUTHORITY_PHOTO', 'SERVICE_PHOTO', 'RELEASE_PHOTO');

-- CreateEnum
CREATE TYPE "AuditAction" AS ENUM ('LOGIN', 'LOGIN_FAILED', 'LOGIN_2FA', 'LOGOUT', 'REGISTER', 'USER_APPROVED', 'USER_REJECTED', 'USER_BLOCKED', 'USER_UNBLOCKED', 'PASSWORD_RESET', 'PASSWORD_CHANGED', 'TWO_FA_ENABLED', 'TWO_FA_DISABLED', 'JOB_CREATED', 'JOB_UPDATED', 'JOB_STATUS_CHANGED', 'JOB_ASSIGNED', 'JOB_ACCEPTED', 'JOB_REJECTED', 'JOB_RELEASED', 'SERVICE_LINKED', 'SERVICE_UNLINKED', 'EMPLOYEE_CREATED', 'EMPLOYEE_DELETED', 'INVOICE_CREATED', 'INVOICE_PAID', 'DSGVO_PERSONAL_DATA_CLEANUP', 'STEUERRECHT_DATA_CLEANUP', 'SETTINGS_UPDATED');

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "role" "UserRole" NOT NULL,
    "name" TEXT NOT NULL,
    "email_verified" BOOLEAN NOT NULL DEFAULT false,
    "totp_enabled" BOOLEAN NOT NULL DEFAULT false,
    "totp_secret" TEXT,
    "is_blocked" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "last_login_at" TIMESTAMP(3),
    "blocked_at" TIMESTAMP(3),

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sessions" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "refresh_token" TEXT NOT NULL,
    "user_agent" TEXT,
    "ip_address" TEXT,
    "expires_at" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "password_reset_tokens" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "token" TEXT NOT NULL,
    "expires_at" TIMESTAMP(3) NOT NULL,
    "used_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "password_reset_tokens_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "email_verification_tokens" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "token" TEXT NOT NULL,
    "expires_at" TIMESTAMP(3) NOT NULL,
    "used_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "email_verification_tokens_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "authorities" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "department" TEXT,
    "street" TEXT,
    "city" TEXT,
    "zip_code" TEXT,
    "state" TEXT,
    "phone" TEXT,
    "email" TEXT,
    "approval_status" "ApprovalStatus" NOT NULL DEFAULT 'PENDING',
    "approved_at" TIMESTAMP(3),
    "rejected_at" TIMESTAMP(3),
    "rejection_reason" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "authorities_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "authority_users" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "authority_id" TEXT NOT NULL,
    "dienstnummer" TEXT NOT NULL,
    "is_main_account" BOOLEAN NOT NULL DEFAULT false,
    "parent_user_id" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "authority_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "authority_towing_company_links" (
    "id" TEXT NOT NULL,
    "authority_id" TEXT NOT NULL,
    "towing_company_id" TEXT NOT NULL,
    "linked_by_user_id" TEXT,
    "linked_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "authority_towing_company_links_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "towing_companies" (
    "id" TEXT NOT NULL,
    "company_name" TEXT NOT NULL,
    "phone" TEXT NOT NULL,
    "email" TEXT,
    "website" TEXT,
    "street" TEXT,
    "city" TEXT,
    "zip_code" TEXT,
    "state" TEXT,
    "yard_street" TEXT,
    "yard_city" TEXT,
    "yard_zip_code" TEXT,
    "yard_lat" DOUBLE PRECISION,
    "yard_lng" DOUBLE PRECISION,
    "opening_hours" TEXT,
    "service_code" TEXT NOT NULL,
    "business_license_path" TEXT,
    "approval_status" "ApprovalStatus" NOT NULL DEFAULT 'PENDING',
    "approved_at" TIMESTAMP(3),
    "rejected_at" TIMESTAMP(3),
    "rejection_reason" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "towing_companies_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "towing_company_pricing" (
    "id" TEXT NOT NULL,
    "towing_company_id" TEXT NOT NULL,
    "tow_cost" DOUBLE PRECISION,
    "daily_cost" DOUBLE PRECISION,
    "processing_fee" DOUBLE PRECISION,
    "empty_trip_fee" DOUBLE PRECISION,
    "night_surcharge" DOUBLE PRECISION,
    "weekend_surcharge" DOUBLE PRECISION,
    "heavy_vehicle_surcharge" DOUBLE PRECISION,
    "time_based_enabled" BOOLEAN NOT NULL DEFAULT false,
    "first_half_hour" DOUBLE PRECISION,
    "additional_half_hour" DOUBLE PRECISION,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "towing_company_pricing_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "towing_company_users" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "towing_company_id" TEXT NOT NULL,
    "is_admin" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "towing_company_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "towing_jobs" (
    "id" TEXT NOT NULL,
    "job_number" TEXT NOT NULL,
    "license_plate" TEXT,
    "vin" TEXT,
    "vehicle_brand" TEXT,
    "vehicle_model" TEXT,
    "vehicle_color" TEXT,
    "location_address" TEXT NOT NULL,
    "location_lat" DOUBLE PRECISION,
    "location_lng" DOUBLE PRECISION,
    "tow_reason" TEXT NOT NULL,
    "job_type" "JobType" NOT NULL DEFAULT 'TOWING',
    "status" "JobStatus" NOT NULL DEFAULT 'PENDING',
    "authority_notes" TEXT,
    "service_notes" TEXT,
    "sicherstellung_reason" TEXT,
    "vehicle_category" "VehicleCategory",
    "ordering_authority" TEXT,
    "contact_attempts" BOOLEAN,
    "contact_attempts_notes" TEXT,
    "estimated_vehicle_value" DOUBLE PRECISION,
    "is_empty_trip" BOOLEAN NOT NULL DEFAULT false,
    "authority_id" TEXT NOT NULL,
    "created_by_user_id" TEXT,
    "created_by_service" BOOLEAN NOT NULL DEFAULT false,
    "towing_company_id" TEXT,
    "owner_first_name" TEXT,
    "owner_last_name" TEXT,
    "owner_street" TEXT,
    "owner_city" TEXT,
    "owner_zip_code" TEXT,
    "owner_phone" TEXT,
    "owner_email" TEXT,
    "payment_method" "PaymentMethod",
    "payment_amount" DOUBLE PRECISION,
    "payment_received_at" TIMESTAMP(3),
    "calculated_costs" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "assigned_at" TIMESTAMP(3),
    "accepted_at" TIMESTAMP(3),
    "rejected_at" TIMESTAMP(3),
    "on_site_at" TIMESTAMP(3),
    "towed_at" TIMESTAMP(3),
    "in_yard_at" TIMESTAMP(3),
    "released_at" TIMESTAMP(3),
    "cancelled_at" TIMESTAMP(3),
    "personal_data_anonymized" BOOLEAN NOT NULL DEFAULT false,
    "personal_data_anonymized_at" TIMESTAMP(3),
    "invoice_data_deleted" BOOLEAN NOT NULL DEFAULT false,
    "invoice_data_deleted_at" TIMESTAMP(3),

    CONSTRAINT "towing_jobs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "towing_job_photos" (
    "id" TEXT NOT NULL,
    "job_id" TEXT NOT NULL,
    "photo_type" "PhotoType" NOT NULL,
    "storage_path" TEXT NOT NULL,
    "file_name" TEXT,
    "mime_type" TEXT,
    "file_size" INTEGER,
    "uploaded_by_user_id" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "is_deleted" BOOLEAN NOT NULL DEFAULT false,
    "deleted_at" TIMESTAMP(3),

    CONSTRAINT "towing_job_photos_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "towing_job_events" (
    "id" TEXT NOT NULL,
    "job_id" TEXT NOT NULL,
    "event_type" TEXT NOT NULL,
    "from_status" "JobStatus",
    "to_status" "JobStatus",
    "description" TEXT,
    "triggered_by_user_id" TEXT,
    "triggered_by_name" TEXT,
    "metadata" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "towing_job_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "invoices" (
    "id" TEXT NOT NULL,
    "invoice_number" TEXT NOT NULL,
    "job_id" TEXT NOT NULL,
    "towing_company_id" TEXT NOT NULL,
    "subtotal" DOUBLE PRECISION NOT NULL,
    "tax_rate" DOUBLE PRECISION NOT NULL DEFAULT 19.0,
    "tax_amount" DOUBLE PRECISION NOT NULL,
    "total_amount" DOUBLE PRECISION NOT NULL,
    "line_items" JSONB NOT NULL,
    "is_paid" BOOLEAN NOT NULL DEFAULT false,
    "paid_at" TIMESTAMP(3),
    "payment_method" "PaymentMethod",
    "pdf_path" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "invoices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "invoice_customer_data" (
    "id" TEXT NOT NULL,
    "invoice_id" TEXT NOT NULL,
    "first_name" TEXT,
    "last_name" TEXT,
    "street" TEXT,
    "city" TEXT,
    "zip_code" TEXT,
    "phone" TEXT,
    "email" TEXT,
    "is_anonymized" BOOLEAN NOT NULL DEFAULT false,
    "anonymized_at" TIMESTAMP(3),

    CONSTRAINT "invoice_customer_data_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "order_documents" (
    "id" TEXT NOT NULL,
    "job_id" TEXT,
    "invoice_id" TEXT,
    "document_type" TEXT NOT NULL,
    "document_name" TEXT NOT NULL,
    "storage_path" TEXT NOT NULL,
    "mime_type" TEXT,
    "file_size" INTEGER,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "order_documents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_logs" (
    "id" TEXT NOT NULL,
    "action" "AuditAction" NOT NULL,
    "user_id" TEXT,
    "user_email" TEXT,
    "user_name" TEXT,
    "entity_type" TEXT,
    "entity_id" TEXT,
    "details" JSONB,
    "ip_address" TEXT,
    "user_agent" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "system_settings" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "value" TEXT NOT NULL,
    "description" TEXT,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "updated_by_user_id" TEXT,

    CONSTRAINT "system_settings_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "invoice_counters" (
    "id" TEXT NOT NULL,
    "towing_company_id" TEXT NOT NULL,
    "year" INTEGER NOT NULL,
    "last_number" INTEGER NOT NULL DEFAULT 0,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "invoice_counters_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_email_idx" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_role_idx" ON "users"("role");

-- CreateIndex
CREATE INDEX "users_created_at_idx" ON "users"("created_at");

-- CreateIndex
CREATE UNIQUE INDEX "sessions_refresh_token_key" ON "sessions"("refresh_token");

-- CreateIndex
CREATE INDEX "sessions_user_id_idx" ON "sessions"("user_id");

-- CreateIndex
CREATE INDEX "sessions_refresh_token_idx" ON "sessions"("refresh_token");

-- CreateIndex
CREATE INDEX "sessions_expires_at_idx" ON "sessions"("expires_at");

-- CreateIndex
CREATE UNIQUE INDEX "password_reset_tokens_token_key" ON "password_reset_tokens"("token");

-- CreateIndex
CREATE INDEX "password_reset_tokens_token_idx" ON "password_reset_tokens"("token");

-- CreateIndex
CREATE INDEX "password_reset_tokens_user_id_idx" ON "password_reset_tokens"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "email_verification_tokens_token_key" ON "email_verification_tokens"("token");

-- CreateIndex
CREATE INDEX "email_verification_tokens_token_idx" ON "email_verification_tokens"("token");

-- CreateIndex
CREATE INDEX "email_verification_tokens_user_id_idx" ON "email_verification_tokens"("user_id");

-- CreateIndex
CREATE INDEX "authorities_name_idx" ON "authorities"("name");

-- CreateIndex
CREATE INDEX "authorities_approval_status_idx" ON "authorities"("approval_status");

-- CreateIndex
CREATE INDEX "authorities_city_idx" ON "authorities"("city");

-- CreateIndex
CREATE UNIQUE INDEX "authority_users_user_id_key" ON "authority_users"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "authority_users_dienstnummer_key" ON "authority_users"("dienstnummer");

-- CreateIndex
CREATE INDEX "authority_users_authority_id_idx" ON "authority_users"("authority_id");

-- CreateIndex
CREATE INDEX "authority_users_dienstnummer_idx" ON "authority_users"("dienstnummer");

-- CreateIndex
CREATE INDEX "authority_users_is_main_account_idx" ON "authority_users"("is_main_account");

-- CreateIndex
CREATE INDEX "authority_towing_company_links_authority_id_idx" ON "authority_towing_company_links"("authority_id");

-- CreateIndex
CREATE INDEX "authority_towing_company_links_towing_company_id_idx" ON "authority_towing_company_links"("towing_company_id");

-- CreateIndex
CREATE UNIQUE INDEX "authority_towing_company_links_authority_id_towing_company__key" ON "authority_towing_company_links"("authority_id", "towing_company_id");

-- CreateIndex
CREATE UNIQUE INDEX "towing_companies_service_code_key" ON "towing_companies"("service_code");

-- CreateIndex
CREATE INDEX "towing_companies_company_name_idx" ON "towing_companies"("company_name");

-- CreateIndex
CREATE INDEX "towing_companies_service_code_idx" ON "towing_companies"("service_code");

-- CreateIndex
CREATE INDEX "towing_companies_approval_status_idx" ON "towing_companies"("approval_status");

-- CreateIndex
CREATE INDEX "towing_companies_city_idx" ON "towing_companies"("city");

-- CreateIndex
CREATE UNIQUE INDEX "towing_company_pricing_towing_company_id_key" ON "towing_company_pricing"("towing_company_id");

-- CreateIndex
CREATE UNIQUE INDEX "towing_company_users_user_id_key" ON "towing_company_users"("user_id");

-- CreateIndex
CREATE INDEX "towing_company_users_towing_company_id_idx" ON "towing_company_users"("towing_company_id");

-- CreateIndex
CREATE UNIQUE INDEX "towing_jobs_job_number_key" ON "towing_jobs"("job_number");

-- CreateIndex
CREATE INDEX "towing_jobs_job_number_idx" ON "towing_jobs"("job_number");

-- CreateIndex
CREATE INDEX "towing_jobs_license_plate_idx" ON "towing_jobs"("license_plate");

-- CreateIndex
CREATE INDEX "towing_jobs_vin_idx" ON "towing_jobs"("vin");

-- CreateIndex
CREATE INDEX "towing_jobs_status_idx" ON "towing_jobs"("status");

-- CreateIndex
CREATE INDEX "towing_jobs_authority_id_idx" ON "towing_jobs"("authority_id");

-- CreateIndex
CREATE INDEX "towing_jobs_towing_company_id_idx" ON "towing_jobs"("towing_company_id");

-- CreateIndex
CREATE INDEX "towing_jobs_created_at_idx" ON "towing_jobs"("created_at");

-- CreateIndex
CREATE INDEX "towing_jobs_released_at_idx" ON "towing_jobs"("released_at");

-- CreateIndex
CREATE INDEX "towing_jobs_personal_data_anonymized_idx" ON "towing_jobs"("personal_data_anonymized");

-- CreateIndex
CREATE INDEX "towing_job_photos_job_id_idx" ON "towing_job_photos"("job_id");

-- CreateIndex
CREATE INDEX "towing_job_photos_photo_type_idx" ON "towing_job_photos"("photo_type");

-- CreateIndex
CREATE INDEX "towing_job_events_job_id_idx" ON "towing_job_events"("job_id");

-- CreateIndex
CREATE INDEX "towing_job_events_event_type_idx" ON "towing_job_events"("event_type");

-- CreateIndex
CREATE INDEX "towing_job_events_created_at_idx" ON "towing_job_events"("created_at");

-- CreateIndex
CREATE UNIQUE INDEX "invoices_invoice_number_key" ON "invoices"("invoice_number");

-- CreateIndex
CREATE INDEX "invoices_invoice_number_idx" ON "invoices"("invoice_number");

-- CreateIndex
CREATE INDEX "invoices_job_id_idx" ON "invoices"("job_id");

-- CreateIndex
CREATE INDEX "invoices_towing_company_id_idx" ON "invoices"("towing_company_id");

-- CreateIndex
CREATE INDEX "invoices_created_at_idx" ON "invoices"("created_at");

-- CreateIndex
CREATE INDEX "invoices_is_paid_idx" ON "invoices"("is_paid");

-- CreateIndex
CREATE UNIQUE INDEX "invoice_customer_data_invoice_id_key" ON "invoice_customer_data"("invoice_id");

-- CreateIndex
CREATE INDEX "order_documents_job_id_idx" ON "order_documents"("job_id");

-- CreateIndex
CREATE INDEX "order_documents_invoice_id_idx" ON "order_documents"("invoice_id");

-- CreateIndex
CREATE INDEX "order_documents_document_type_idx" ON "order_documents"("document_type");

-- CreateIndex
CREATE INDEX "audit_logs_action_idx" ON "audit_logs"("action");

-- CreateIndex
CREATE INDEX "audit_logs_user_id_idx" ON "audit_logs"("user_id");

-- CreateIndex
CREATE INDEX "audit_logs_entity_type_entity_id_idx" ON "audit_logs"("entity_type", "entity_id");

-- CreateIndex
CREATE INDEX "audit_logs_created_at_idx" ON "audit_logs"("created_at");

-- CreateIndex
CREATE UNIQUE INDEX "system_settings_key_key" ON "system_settings"("key");

-- CreateIndex
CREATE UNIQUE INDEX "invoice_counters_towing_company_id_key" ON "invoice_counters"("towing_company_id");

-- CreateIndex
CREATE UNIQUE INDEX "invoice_counters_towing_company_id_year_key" ON "invoice_counters"("towing_company_id", "year");

-- AddForeignKey
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "password_reset_tokens" ADD CONSTRAINT "password_reset_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "email_verification_tokens" ADD CONSTRAINT "email_verification_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "authority_users" ADD CONSTRAINT "authority_users_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "authority_users" ADD CONSTRAINT "authority_users_authority_id_fkey" FOREIGN KEY ("authority_id") REFERENCES "authorities"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "authority_users" ADD CONSTRAINT "authority_users_parent_user_id_fkey" FOREIGN KEY ("parent_user_id") REFERENCES "authority_users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "authority_towing_company_links" ADD CONSTRAINT "authority_towing_company_links_authority_id_fkey" FOREIGN KEY ("authority_id") REFERENCES "authorities"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "authority_towing_company_links" ADD CONSTRAINT "authority_towing_company_links_towing_company_id_fkey" FOREIGN KEY ("towing_company_id") REFERENCES "towing_companies"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_company_pricing" ADD CONSTRAINT "towing_company_pricing_towing_company_id_fkey" FOREIGN KEY ("towing_company_id") REFERENCES "towing_companies"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_company_users" ADD CONSTRAINT "towing_company_users_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_company_users" ADD CONSTRAINT "towing_company_users_towing_company_id_fkey" FOREIGN KEY ("towing_company_id") REFERENCES "towing_companies"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_jobs" ADD CONSTRAINT "towing_jobs_authority_id_fkey" FOREIGN KEY ("authority_id") REFERENCES "authorities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_jobs" ADD CONSTRAINT "towing_jobs_created_by_user_id_fkey" FOREIGN KEY ("created_by_user_id") REFERENCES "authority_users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_jobs" ADD CONSTRAINT "towing_jobs_towing_company_id_fkey" FOREIGN KEY ("towing_company_id") REFERENCES "towing_companies"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_job_photos" ADD CONSTRAINT "towing_job_photos_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "towing_jobs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "towing_job_events" ADD CONSTRAINT "towing_job_events_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "towing_jobs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "invoices" ADD CONSTRAINT "invoices_job_id_fkey" FOREIGN KEY ("job_id") REFERENCES "towing_jobs"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "invoices" ADD CONSTRAINT "invoices_towing_company_id_fkey" FOREIGN KEY ("towing_company_id") REFERENCES "towing_companies"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "invoice_customer_data" ADD CONSTRAINT "invoice_customer_data_invoice_id_fkey" FOREIGN KEY ("invoice_id") REFERENCES "invoices"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;
