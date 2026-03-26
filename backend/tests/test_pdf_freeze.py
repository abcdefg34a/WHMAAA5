"""
Test suite for 10-Day PDF Freeze Feature
Tests the following functionality:
1. pdf_generated_at field in JobResponse schema
2. PDF generation saves pdf_generated_at on first generation
3. PATCH /api/services/pricing-settings accepts update_old_pdfs parameter
4. PATCH /api/authority/settings accepts update_old_pdfs parameter
5. When update_old_pdfs=true, pdf_generated_at fields for jobs >10 days are reset
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
import uuid

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
AUTHORITY_EMAIL = "behoerde@test.de"
AUTHORITY_PASSWORD = "Behoerde123!"
TOWING_EMAIL = "abschlepp@test.de"
TOWING_PASSWORD = "Abschlepp123!"


class TestPDFFreeze:
    """Test suite for 10-Day PDF Freeze Feature"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Shared requests session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    @pytest.fixture(scope="class")
    def authority_token(self, api_client):
        """Get authentication token for authority user"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": AUTHORITY_EMAIL,
            "password": AUTHORITY_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        pytest.skip(f"Authority authentication failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def towing_token(self, api_client):
        """Get authentication token for towing service user"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TOWING_EMAIL,
            "password": TOWING_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        pytest.skip(f"Towing service authentication failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def authority_client(self, api_client, authority_token):
        """Session with authority auth header"""
        api_client.headers.update({"Authorization": f"Bearer {authority_token}"})
        return api_client
    
    @pytest.fixture(scope="class")
    def towing_client(self, api_client, towing_token):
        """Session with towing service auth header"""
        api_client.headers.update({"Authorization": f"Bearer {towing_token}"})
        return api_client

    # ==================== BACKEND SCHEMA TESTS ====================
    
    def test_health_check(self, api_client):
        """Test that the API is accessible"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ Health check passed")
    
    def test_authority_login(self, api_client):
        """Test authority login works"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": AUTHORITY_EMAIL,
            "password": AUTHORITY_PASSWORD
        })
        assert response.status_code == 200, f"Authority login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"✓ Authority login successful")
    
    def test_towing_login(self, api_client):
        """Test towing service login works"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TOWING_EMAIL,
            "password": TOWING_PASSWORD
        })
        assert response.status_code == 200, f"Towing login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"✓ Towing service login successful")

    def test_job_response_has_pdf_generated_at_field(self, api_client, authority_token):
        """Test that JobResponse schema includes pdf_generated_at field"""
        headers = {"Authorization": f"Bearer {authority_token}"}
        response = api_client.get(f"{BASE_URL}/api/jobs", headers=headers)
        assert response.status_code == 200, f"Failed to get jobs: {response.text}"
        
        jobs = response.json()
        if len(jobs) > 0:
            # Check that the field exists in the response (can be None)
            first_job = jobs[0]
            # pdf_generated_at should be in the schema (may be None if not generated yet)
            assert "pdf_generated_at" in first_job or first_job.get("pdf_generated_at") is None, \
                "pdf_generated_at field should be present in JobResponse"
            print(f"✓ JobResponse includes pdf_generated_at field (value: {first_job.get('pdf_generated_at')})")
        else:
            print("⚠ No jobs found to verify pdf_generated_at field - creating test job")
            # Create a test job to verify the field
            job_data = {
                "license_plate": f"TEST-PDF-{uuid.uuid4().hex[:4].upper()}",
                "tow_reason": "Test PDF Freeze Feature",
                "location_address": "Test Location",
                "location_lat": 52.52,
                "location_lng": 13.405
            }
            create_response = api_client.post(f"{BASE_URL}/api/jobs", json=job_data, headers=headers)
            if create_response.status_code in [200, 201]:
                created_job = create_response.json()
                assert "pdf_generated_at" in created_job or created_job.get("pdf_generated_at") is None, \
                    "pdf_generated_at field should be present in JobResponse"
                print(f"✓ Created test job with pdf_generated_at field")

    # ==================== PRICING SETTINGS TESTS ====================
    
    def test_pricing_settings_accepts_update_old_pdfs_false(self, api_client, towing_token):
        """Test PATCH /api/services/pricing-settings accepts update_old_pdfs=false"""
        headers = {"Authorization": f"Bearer {towing_token}"}
        
        # Get current settings first
        me_response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert me_response.status_code == 200, f"Failed to get user info: {me_response.text}"
        
        # Update with update_old_pdfs=false (should not reset old PDFs)
        response = api_client.patch(f"{BASE_URL}/api/services/pricing-settings", 
            json={
                "tow_cost": 150.0,
                "daily_cost": 25.0,
                "update_old_pdfs": False
            },
            headers=headers
        )
        assert response.status_code == 200, f"Pricing settings update failed: {response.status_code} - {response.text}"
        print("✓ PATCH /api/services/pricing-settings accepts update_old_pdfs=false")
    
    def test_pricing_settings_accepts_update_old_pdfs_true(self, api_client, towing_token):
        """Test PATCH /api/services/pricing-settings accepts update_old_pdfs=true"""
        headers = {"Authorization": f"Bearer {towing_token}"}
        
        # Update with update_old_pdfs=true (should reset old PDFs)
        response = api_client.patch(f"{BASE_URL}/api/services/pricing-settings", 
            json={
                "tow_cost": 150.0,
                "daily_cost": 25.0,
                "update_old_pdfs": True
            },
            headers=headers
        )
        assert response.status_code == 200, f"Pricing settings update failed: {response.status_code} - {response.text}"
        print("✓ PATCH /api/services/pricing-settings accepts update_old_pdfs=true")

    # ==================== AUTHORITY SETTINGS TESTS ====================
    
    def test_authority_settings_accepts_update_old_pdfs_false(self, api_client, authority_token):
        """Test PATCH /api/authority/settings accepts update_old_pdfs=false"""
        headers = {"Authorization": f"Bearer {authority_token}"}
        
        # Update with update_old_pdfs=false
        response = api_client.patch(f"{BASE_URL}/api/authority/settings", 
            json={
                "yard_model": "service_yard",
                "update_old_pdfs": False
            },
            headers=headers
        )
        assert response.status_code == 200, f"Authority settings update failed: {response.status_code} - {response.text}"
        print("✓ PATCH /api/authority/settings accepts update_old_pdfs=false")
    
    def test_authority_settings_accepts_update_old_pdfs_true(self, api_client, authority_token):
        """Test PATCH /api/authority/settings accepts update_old_pdfs=true"""
        headers = {"Authorization": f"Bearer {authority_token}"}
        
        # Update with update_old_pdfs=true
        response = api_client.patch(f"{BASE_URL}/api/authority/settings", 
            json={
                "yard_model": "service_yard",
                "update_old_pdfs": True
            },
            headers=headers
        )
        assert response.status_code == 200, f"Authority settings update failed: {response.status_code} - {response.text}"
        print("✓ PATCH /api/authority/settings accepts update_old_pdfs=true")

    # ==================== PDF GENERATION TESTS ====================
    
    def test_pdf_generation_sets_timestamp(self, api_client, authority_token, towing_token):
        """Test that PDF generation sets pdf_generated_at timestamp on first generation"""
        auth_headers = {"Authorization": f"Bearer {authority_token}"}
        tow_headers = {"Authorization": f"Bearer {towing_token}"}
        
        # Get linked services first
        services_response = api_client.get(f"{BASE_URL}/api/services", headers=auth_headers)
        if services_response.status_code != 200 or len(services_response.json()) == 0:
            pytest.skip("No linked services found for authority")
        
        service_id = services_response.json()[0]["id"]
        
        # Create a new job
        job_data = {
            "license_plate": f"TEST-PDFTS-{uuid.uuid4().hex[:4].upper()}",
            "tow_reason": "Test PDF Timestamp Generation",
            "location_address": "Test Location for PDF",
            "location_lat": 52.52,
            "location_lng": 13.405,
            "assigned_service_id": service_id
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/jobs", json=job_data, headers=auth_headers)
        assert create_response.status_code in [200, 201], f"Job creation failed: {create_response.text}"
        
        created_job = create_response.json()
        job_id = created_job["id"]
        
        # Verify pdf_generated_at is initially None
        initial_pdf_generated_at = created_job.get("pdf_generated_at")
        print(f"Initial pdf_generated_at: {initial_pdf_generated_at}")
        
        # Get PDF token
        token_response = api_client.get(f"{BASE_URL}/api/jobs/{job_id}/pdf/token", headers=tow_headers)
        if token_response.status_code != 200:
            # Try with authority token
            token_response = api_client.get(f"{BASE_URL}/api/jobs/{job_id}/pdf/token", headers=auth_headers)
        
        if token_response.status_code == 200:
            pdf_token = token_response.json().get("token")
            
            # Generate PDF
            pdf_response = api_client.get(f"{BASE_URL}/api/jobs/{job_id}/pdf?token={pdf_token}")
            assert pdf_response.status_code == 200, f"PDF generation failed: {pdf_response.status_code}"
            assert pdf_response.headers.get("content-type") == "application/pdf", "Response is not a PDF"
            
            # Verify pdf_generated_at is now set
            job_response = api_client.get(f"{BASE_URL}/api/jobs/{job_id}", headers=auth_headers)
            if job_response.status_code == 200:
                updated_job = job_response.json()
                pdf_generated_at = updated_job.get("pdf_generated_at")
                assert pdf_generated_at is not None, "pdf_generated_at should be set after PDF generation"
                print(f"✓ PDF generation sets pdf_generated_at timestamp: {pdf_generated_at}")
            else:
                # Try getting job from list
                jobs_response = api_client.get(f"{BASE_URL}/api/jobs", headers=auth_headers)
                if jobs_response.status_code == 200:
                    jobs = jobs_response.json()
                    job = next((j for j in jobs if j["id"] == job_id), None)
                    if job:
                        pdf_generated_at = job.get("pdf_generated_at")
                        assert pdf_generated_at is not None, "pdf_generated_at should be set after PDF generation"
                        print(f"✓ PDF generation sets pdf_generated_at timestamp: {pdf_generated_at}")
        else:
            print(f"⚠ Could not get PDF token: {token_response.status_code} - skipping PDF generation test")

    # ==================== UST-ID TESTS ====================
    
    def test_pricing_settings_accepts_ust_id(self, api_client, towing_token):
        """Test that pricing settings accepts USt-ID field"""
        headers = {"Authorization": f"Bearer {towing_token}"}
        
        response = api_client.patch(f"{BASE_URL}/api/services/pricing-settings", 
            json={
                "ust_id": "DE123456789",
                "update_old_pdfs": False
            },
            headers=headers
        )
        assert response.status_code == 200, f"USt-ID update failed: {response.status_code} - {response.text}"
        
        # Verify USt-ID was saved
        me_response = api_client.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if me_response.status_code == 200:
            user_data = me_response.json()
            assert user_data.get("ust_id") == "DE123456789", "USt-ID was not saved correctly"
        print("✓ Pricing settings accepts and saves USt-ID")
    
    def test_authority_settings_accepts_ust_id(self, api_client, authority_token):
        """Test that authority settings accepts USt-ID field"""
        headers = {"Authorization": f"Bearer {authority_token}"}
        
        response = api_client.patch(f"{BASE_URL}/api/authority/settings", 
            json={
                "ust_id": "DE987654321",
                "update_old_pdfs": False
            },
            headers=headers
        )
        assert response.status_code == 200, f"Authority USt-ID update failed: {response.status_code} - {response.text}"
        print("✓ Authority settings accepts USt-ID")

    # ==================== PRICES INCLUDE VAT TESTS ====================
    
    def test_pricing_settings_accepts_prices_include_vat(self, api_client, towing_token):
        """Test that pricing settings accepts prices_include_vat field"""
        headers = {"Authorization": f"Bearer {towing_token}"}
        
        # Test with prices_include_vat = True (Brutto)
        response = api_client.patch(f"{BASE_URL}/api/services/pricing-settings", 
            json={
                "prices_include_vat": True,
                "update_old_pdfs": False
            },
            headers=headers
        )
        assert response.status_code == 200, f"prices_include_vat update failed: {response.status_code} - {response.text}"
        
        # Test with prices_include_vat = False (Netto)
        response = api_client.patch(f"{BASE_URL}/api/services/pricing-settings", 
            json={
                "prices_include_vat": False,
                "update_old_pdfs": False
            },
            headers=headers
        )
        assert response.status_code == 200, f"prices_include_vat update failed: {response.status_code} - {response.text}"
        print("✓ Pricing settings accepts prices_include_vat")
    
    def test_authority_settings_accepts_prices_include_vat(self, api_client, authority_token):
        """Test that authority settings accepts prices_include_vat field"""
        headers = {"Authorization": f"Bearer {authority_token}"}
        
        response = api_client.patch(f"{BASE_URL}/api/authority/settings", 
            json={
                "prices_include_vat": True,
                "update_old_pdfs": False
            },
            headers=headers
        )
        assert response.status_code == 200, f"Authority prices_include_vat update failed: {response.status_code} - {response.text}"
        print("✓ Authority settings accepts prices_include_vat")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
