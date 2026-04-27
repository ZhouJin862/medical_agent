"""
Integration tests for MCP clients.

These tests verify that MCP clients can properly communicate
with their respective MCP servers using comprehensive test coverage.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path before any other imports to avoid mcp package shadowing
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Any, Dict, List

from src.infrastructure.mcp.clients.profile_client import ProfileMCPClient
from src.infrastructure.mcp.clients.triage_client import TriageMCPClient
from src.infrastructure.mcp.clients.medication_client import MedicationMCPClient
from src.infrastructure.mcp.clients.service_client import ServiceMCPClient
from src.infrastructure.mcp.client_factory import MCPClientFactory
from src.infrastructure.mcp.base_client import MCPConnectionError, MCPToolError


# ========== Fixtures ==========

@pytest.fixture
def mock_mcp_response():
    """Create a mock MCP tool response."""
    def _create_response(data: Dict[str, Any]) -> Any:
        mock_response = Mock()
        mock_content_item = Mock()
        mock_content_item.text = json.dumps(data, ensure_ascii=False)
        mock_response.content = [mock_content_item]
        return mock_response
    return _create_response


@pytest.fixture
def sample_patient_profile():
    """Sample patient profile data."""
    return {
        "patient_id": "P001",
        "name": "张三",
        "gender": "male",
        "age": 45,
        "birth_date": "1979-01-01",
        "phone": "13800138000",
        "email": "zhangsan@example.com"
    }


@pytest.fixture
def sample_vital_signs():
    """Sample vital signs data."""
    return {
        "patient_id": "P001",
        "blood_pressure": {
            "systolic": 120,
            "diastolic": 80
        },
        "blood_glucose": {
            "fasting": 5.5,
            "postprandial": 7.8
        },
        "lipids": {
            "total_cholesterol": 5.2,
            "ldl": 3.0,
            "hdl": 1.2,
            "triglycerides": 1.8
        },
        "uric_acid": 380,
        "bmi": 24.5,
        "waist_circumference": 85,
        "measured_at": "2024-01-15T10:30:00Z"
    }


@pytest.fixture
def sample_medical_records():
    """Sample medical records data."""
    return {
        "patient_id": "P001",
        "diagnoses": [
            {"code": "I10", "name": "Essential hypertension", "date": "2023-06-01"}
        ],
        "surgeries": [],
        "allergies": ["Penicillin"],
        "medications": ["Amlodipine", "Lisinopril"],
        "chronic_diseases": ["Hypertension"],
        "family_history": ["Diabetes", "Hypertension"]
    }


@pytest.fixture
def sample_hospitals():
    """Sample hospital recommendations."""
    return {
        "hospitals": [
            {
                "hospital_id": "H001",
                "name": "北京协和医院",
                "level": "tertiary",
                "distance_km": 5.2,
                "address": "北京市东城区帅府园1号",
                "emergency_available": True,
                "recommended_departments": ["Cardiology", "Internal Medicine"],
                "estimated_travel_time": "15 minutes"
            },
            {
                "hospital_id": "H002",
                "name": "北京同仁医院",
                "level": "tertiary",
                "distance_km": 8.5,
                "address": "北京市东城区东交民巷1号",
                "emergency_available": True,
                "recommended_departments": ["Cardiology"],
                "estimated_travel_time": "25 minutes"
            }
        ]
    }


@pytest.fixture
def sample_departments():
    """Sample department recommendations."""
    return {
        "departments": [
            {
                "department_id": "D001",
                "name": "心血管内科",
                "priority": "high",
                "reason": "Based on symptoms of chest pain and shortness of breath",
                "related_symptoms": ["chest pain", "shortness of breath"]
            },
            {
                "department_id": "D002",
                "name": "急诊科",
                "priority": "medium",
                "reason": "For immediate evaluation if symptoms worsen",
                "related_symptoms": []
            }
        ]
    }


@pytest.fixture
def sample_doctors():
    """Sample doctor recommendations."""
    return {
        "doctors": [
            {
                "doctor_id": "DR001",
                "name": "王医生",
                "title": "主任医师",
                "department": "心血管内科",
                "specialty": "冠心病",
                "expertise_areas": ["高血压", "冠心病", "心力衰竭"],
                "schedule": {
                    "monday": "09:00-12:00",
                    "wednesday": "14:00-17:00",
                    "friday": "09:00-12:00"
                },
                "consultation_fee": 100
            }
        ]
    }


@pytest.fixture
def sample_medication_check():
    """Sample medication check result."""
    return {
        "medication_name": "Amlodipine",
        "indication_match": True,
        "dosage_appropriate": True,
        "dosage_warnings": [],
        "interactions": [],
        "contraindications": [],
        "special_populations": {
            "elderly": "Consider lower starting dose",
            "renal_impairment": "No adjustment needed"
        },
        "recommendations": [
            "Take once daily",
            "Can be taken with or without food"
        ]
    }


@pytest.fixture
def sample_drug_recommendations():
    """Sample drug recommendations."""
    return {
        "condition": "Hypertension",
        "first_line_recommendations": [
            {
                "drug": "Amlodipine",
                "dosage": "5mg once daily",
                "evidence_level": "A"
            },
            {
                "drug": "Lisinopril",
                "dosage": "10mg once daily",
                "evidence_level": "A"
            }
        ],
        "alternative_recommendations": [
            {
                "drug": "Hydrochlorothiazide",
                "dosage": "12.5mg once daily",
                "evidence_level": "B"
            }
        ],
        "contraindicated_drugs": [],
        "special_considerations": [
            "Monitor blood pressure regularly",
            "Check renal function every 6 months"
        ],
        "monitoring_parameters": [
            "Blood pressure",
            "Serum creatinine",
            "Potassium levels"
        ],
        "lifestyle_recommendations": [
            "Low sodium diet",
            "Regular exercise",
            "Weight management"
        ]
    }


@pytest.fixture
def sample_insurance_recommendations():
    """Sample insurance recommendations."""
    return {
        "chronic_disease_insurance": [
            {
                "product_name": "慢性病关爱保",
                "coverage": "Covers hypertension, diabetes complications",
                "premium_estimate": "2000-5000 CNY/year",
                "claim_conditions": ["Confirmed diagnosis", "Regular treatment records"]
            }
        ],
        "critical_illness_insurance": [
            {
                "product_name": "重大疾病险",
                "coverage": "Covers 100+ critical illnesses",
                "premium_estimate": "5000-15000 CNY/year",
                "claim_conditions": ["Pathology confirmation", "Specific disease criteria"]
            }
        ],
        "medical_insurance": [
            {
                "product_name": "百万医疗险",
                "coverage": "Hospitalization expenses, outpatient surgery",
                "premium_estimate": "300-1000 CNY/year",
                "claim_conditions": ["Hospitalization >30 days", "Reimbursement with receipts"]
            }
        ],
        "coverage_details": "See policy documents for complete coverage",
        "purchase_links": ["https://example.com/purchase"]
    }


@pytest.fixture
def sample_health_services():
    """Sample health service recommendations."""
    return {
        "disease_management_services": [
            {
                "service_name": "高血压管理计划",
                "description": "Comprehensive hypertension management",
                "duration": "12 weeks",
                "price": "2000 CNY"
            }
        ],
        "health_promotion_services": [
            {
                "service_name": "健康生活方式指导",
                "description": "Personalized lifestyle coaching",
                "duration": "8 weeks",
                "price": "1500 CNY"
            }
        ],
        "rehabilitation_services": [],
        "preventive_services": [
            {
                "service_name": "定期健康体检",
                "description": "Annual comprehensive checkup",
                "frequency": "Once per year",
                "price": "1000 CNY"
            }
        ],
        "service_details": "All services include professional guidance",
        "pricing": "Package discounts available",
        "booking_info": "Call 400-xxx-xxxx or book online"
    }


# ========== ProfileMCPClient Tests ==========

@pytest.mark.asyncio
@pytest.mark.integration
class TestProfileMCPClient:
    """Test ProfileMCPClient (健康档案)."""

    async def test_client_initialization(self):
        """Test ProfileMCPClient initialization."""
        client = ProfileMCPClient()
        assert client.server_name == "profile_server"
        assert client.transport == "stdio"
        assert client.command is not None
        assert "profile_server" in client.command

    async def test_get_patient_profile_success(self, mock_mcp_response, sample_patient_profile):
        """Test successfully getting patient profile."""
        client = ProfileMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_patient_profile)

            result = await client.get_patient_profile("P001")

            assert result["patient_id"] == "P001"
            assert result["name"] == "张三"
            assert result["age"] == 45
            mock_call.assert_called_once_with("get_patient_profile", {"patient_id": "P001"})

    async def test_get_patient_profile_with_response_parsing(self, mock_mcp_response, sample_patient_profile):
        """Test patient profile with proper response parsing."""
        client = ProfileMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_patient_profile)

            result = await client.get_patient_profile("P001")

            assert "patient_id" in result
            assert "name" in result
            assert "gender" in result
            assert isinstance(result["age"], int)

    async def test_get_vital_signs_success(self, mock_mcp_response, sample_vital_signs):
        """Test successfully getting vital signs."""
        client = ProfileMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_vital_signs)

            result = await client.get_vital_signs("P001")

            assert result["patient_id"] == "P001"
            assert "blood_pressure" in result
            assert "blood_glucose" in result
            assert result["blood_pressure"]["systolic"] == 120
            mock_call.assert_called_once_with("get_vital_signs", {"patient_id": "P001"})

    async def test_get_medical_records_success(self, mock_mcp_response, sample_medical_records):
        """Test successfully getting medical records."""
        client = ProfileMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_medical_records)

            result = await client.get_medical_records("P001")

            assert result["patient_id"] == "P001"
            assert "diagnoses" in result
            assert "allergies" in result
            assert len(result["diagnoses"]) > 0
            mock_call.assert_called_once_with("get_medical_records", {"patient_id": "P001"})

    async def test_get_lab_results_without_filter(self, mock_mcp_response):
        """Test getting lab results without test type filter."""
        lab_results = {
            "patient_id": "P001",
            "blood_count": {"hemoglobin": 140, "white_blood_cells": 6.5},
            "metabolic_panel": {"glucose": 5.5, "creatinine": 80},
            "tested_at": "2024-01-15T10:30:00Z"
        }
        client = ProfileMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(lab_results)

            result = await client.get_lab_results("P001")

            assert result["patient_id"] == "P001"
            assert "blood_count" in result
            mock_call.assert_called_once_with("get_lab_results", {"patient_id": "P001"})

    async def test_get_lab_results_with_filter(self, mock_mcp_response):
        """Test getting lab results with test type filter."""
        lab_results = {
            "patient_id": "P001",
            "blood_count": {"hemoglobin": 140, "white_blood_cells": 6.5},
            "tested_at": "2024-01-15T10:30:00Z"
        }
        client = ProfileMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(lab_results)

            result = await client.get_lab_results("P001", test_type="blood_count")

            assert result["patient_id"] == "P001"
            mock_call.assert_called_once_with(
                "get_lab_results",
                {"patient_id": "P001", "test_type": "blood_count"}
            )

    async def test_get_patient_profile_error_handling(self):
        """Test error handling when getting patient profile fails."""
        client = ProfileMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Server error")

            with pytest.raises(MCPToolError, match="Failed to get patient profile"):
                await client.get_patient_profile("P001")

    async def test_parse_tool_result_with_content_format(self):
        """Test parsing tool result with content format."""
        client = ProfileMCPClient()
        mock_result = Mock()
        mock_content = Mock()
        mock_content.text = '{"key": "value"}'
        mock_result.content = [mock_content]

        result = client._parse_tool_result(mock_result)
        assert result == {"key": "value"}

    async def test_parse_tool_result_with_dict_format(self):
        """Test parsing tool result with dict format."""
        client = ProfileMCPClient()
        mock_result = {"key": "value"}

        result = client._parse_tool_result(mock_result)
        assert result == {"key": "value"}

    async def test_parse_tool_result_invalid_json(self):
        """Test parsing tool result with invalid JSON."""
        client = ProfileMCPClient()
        mock_result = Mock()
        mock_content = Mock()
        mock_content.text = "Not valid JSON"
        mock_result.content = [mock_content]

        result = client._parse_tool_result(mock_result)
        assert result == {"raw": "Not valid JSON"}


# ========== TriageMCPClient Tests ==========

@pytest.mark.asyncio
@pytest.mark.integration
class TestTriageMCPClient:
    """Test TriageMCPClient (分诊导医)."""

    async def test_client_initialization(self):
        """Test TriageMCPClient initialization."""
        client = TriageMCPClient()
        assert client.server_name == "triage_server"
        assert client.transport == "stdio"
        assert "triage_server" in client.command

    async def test_get_hospitals_basic(self, mock_mcp_response, sample_hospitals):
        """Test getting hospitals with basic parameters."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_hospitals)

            result = await client.get_hospitals("P001")

            # get_hospitals returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            mock_call.assert_called_once()

    async def test_get_hospitals_with_location(self, mock_mcp_response, sample_hospitals):
        """Test getting hospitals with location parameter."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_hospitals)

            result = await client.get_hospitals("P001", severity="severe", location="Beijing", radius_km=30)

            # get_hospitals returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            mock_call.assert_called_once_with(
                "get_hospitals",
                {
                    "patient_id": "P001",
                    "severity": "severe",
                    "radius_km": 30,
                    "location": "Beijing"
                }
            )

    async def test_get_hospitals_result_structure(self, mock_mcp_response, sample_hospitals):
        """Test hospital result structure."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_hospitals)

            result = await client.get_hospitals("P001")

            # get_hospitals returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            hospital = result[0]
            assert "hospital_id" in hospital
            assert "name" in hospital
            assert "level" in hospital
            assert "distance_km" in hospital

    async def test_get_departments_with_symptoms(self, mock_mcp_response, sample_departments):
        """Test getting departments with symptoms."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_departments)

            result = await client.get_departments("P001", symptoms=["headache", "dizziness"])

            # get_departments returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            mock_call.assert_called_once_with(
                "get_departments",
                {"patient_id": "P001", "symptoms": ["headache", "dizziness"]}
            )

    async def test_get_departments_with_diagnosis(self, mock_mcp_response, sample_departments):
        """Test getting departments with diagnosis."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_departments)

            result = await client.get_departments("P001", diagnosis="Migraine")

            # get_departments returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            mock_call.assert_called_once_with(
                "get_departments",
                {"patient_id": "P001", "diagnosis": "Migraine"}
            )

    async def test_get_departments_result_structure(self, mock_mcp_response, sample_departments):
        """Test department result structure."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_departments)

            result = await client.get_departments("P001", symptoms=["chest pain"])

            # get_departments returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            department = result[0]
            assert "department_id" in department
            assert "name" in department
            assert "priority" in department
            assert "reason" in department

    async def test_get_doctors_basic(self, mock_mcp_response, sample_doctors):
        """Test getting doctors with basic parameters."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_doctors)

            result = await client.get_doctors("P001", department="Cardiology")

            # get_doctors returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            mock_call.assert_called_once_with(
                "get_doctors",
                {"patient_id": "P001", "department": "Cardiology", "need_expert": False}
            )

    async def test_get_doctors_with_specialty(self, mock_mcp_response, sample_doctors):
        """Test getting doctors with specialty filter."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_doctors)

            result = await client.get_doctors(
                "P001",
                department="Cardiology",
                specialty="Interventional Cardiology",
                need_expert=True
            )

            # get_doctors returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            mock_call.assert_called_once_with(
                "get_doctors",
                {
                    "patient_id": "P001",
                    "department": "Cardiology",
                    "need_expert": True,
                    "specialty": "Interventional Cardiology"
                }
            )

    async def test_get_doctors_result_structure(self, mock_mcp_response, sample_doctors):
        """Test doctor result structure."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_doctors)

            result = await client.get_doctors("P001", department="Cardiology")

            # get_doctors returns a list directly
            assert isinstance(result, list)
            assert len(result) > 0
            doctor = result[0]
            assert "doctor_id" in doctor
            assert "name" in doctor
            assert "title" in doctor
            assert "department" in doctor
            assert "schedule" in doctor

    async def test_get_triage_advice(self, mock_mcp_response):
        """Test getting triage advice."""
        triage_advice = {
            "urgency_level": "urgent",
            "recommended_timing": "Within 24 hours",
            "recommended_department": "Cardiology",
            "self_care_instructions": ["Rest", "Avoid strenuous activity"],
            "warning_signs": ["Chest pain", "Shortness of breath", "Fainting"]
        }
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(triage_advice)

            result = await client.get_triage_advice(
                "P001",
                symptoms=["chest pain", "shortness of breath"]
            )

            assert result["urgency_level"] == "urgent"
            assert "recommended_department" in result
            assert len(result["warning_signs"]) > 0

    async def test_get_triage_advice_with_urgency(self, mock_mcp_response):
        """Test getting triage advice with urgency assessment."""
        triage_advice = {
            "urgency_level": "emergency",
            "recommended_timing": "Immediately",
            "recommended_department": "Emergency"
        }
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(triage_advice)

            result = await client.get_triage_advice(
                "P001",
                symptoms=["severe chest pain"],
                urgency_assessment="emergency"
            )

            assert result["urgency_level"] == "emergency"
            mock_call.assert_called_once_with(
                "get_triage_advice",
                {
                    "patient_id": "P001",
                    "symptoms": ["severe chest pain"],
                    "urgency_assessment": "emergency"
                }
            )

    async def test_get_hospitals_error_handling(self):
        """Test error handling for get_hospitals."""
        client = TriageMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Service unavailable")

            with pytest.raises(MCPToolError, match="Failed to get hospitals"):
                await client.get_hospitals("P001")


# ========== MedicationMCPClient Tests ==========

@pytest.mark.asyncio
@pytest.mark.integration
class TestMedicationMCPClient:
    """Test MedicationMCPClient (合理用药)."""

    async def test_client_initialization(self):
        """Test MedicationMCPClient initialization."""
        client = MedicationMCPClient()
        assert client.server_name == "medication_server"
        assert client.transport == "stdio"
        assert "medication_server" in client.command

    async def test_check_medication_basic(self, mock_mcp_response, sample_medication_check):
        """Test basic medication checking."""
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_medication_check)

            result = await client.check_medication("P001", "Amlodipine")

            assert result["medication_name"] == "Amlodipine"
            assert result["indication_match"] is True
            mock_call.assert_called_once_with(
                "check_medication",
                {"patient_id": "P001", "medication": "Amlodipine"}
            )

    async def test_check_medication_with_dosage(self, mock_mcp_response, sample_medication_check):
        """Test medication checking with dosage."""
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_medication_check)

            result = await client.check_medication(
                "P001",
                "Amlodipine",
                dosage="5mg",
                frequency="once daily"
            )

            assert result["medication_name"] == "Amlodipine"
            mock_call.assert_called_once_with(
                "check_medication",
                {
                    "patient_id": "P001",
                    "medication": "Amlodipine",
                    "dosage": "5mg",
                    "frequency": "once daily"
                }
            )

    async def test_check_medication_with_interactions(self, mock_mcp_response):
        """Test medication checking with current medications."""
        medication_check = {
            "medication_name": "Warfarin",
            "interactions": [
                {
                    "drug": "Aspirin",
                    "severity": "moderate",
                    "description": "Increased bleeding risk"
                }
            ],
            "recommendations": ["Monitor INR regularly"]
        }
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(medication_check)

            result = await client.check_medication(
                "P001",
                "Warfarin",
                current_medications=["Aspirin", "Lisinopril"]
            )

            assert len(result["interactions"]) > 0
            mock_call.assert_called_once_with(
                "check_medication",
                {
                    "patient_id": "P001",
                    "medication": "Warfarin",
                    "current_medications": ["Aspirin", "Lisinopril"]
                }
            )

    async def test_recommend_drugs_basic(self, mock_mcp_response, sample_drug_recommendations):
        """Test basic drug recommendations."""
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_drug_recommendations)

            result = await client.recommend_drugs("P001", "Hypertension")

            assert result["condition"] == "Hypertension"
            assert len(result["first_line_recommendations"]) > 0
            mock_call.assert_called_once_with(
                "recommend_drugs",
                {"patient_id": "P001", "condition": "Hypertension", "severity": "moderate"}
            )

    async def test_recommend_drugs_with_parameters(self, mock_mcp_response, sample_drug_recommendations):
        """Test drug recommendations with all parameters."""
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_drug_recommendations)

            result = await client.recommend_drugs(
                "P001",
                "Hypertension",
                severity="severe",
                patient_age=75,
                renal_function="moderate_impairment",
                hepatic_function="normal",
                allergies=["Penicillin"]
            )

            assert result["condition"] == "Hypertension"
            mock_call.assert_called_once_with(
                "recommend_drugs",
                {
                    "patient_id": "P001",
                    "condition": "Hypertension",
                    "severity": "severe",
                    "patient_age": 75,
                    "renal_function": "moderate_impairment",
                    "hepatic_function": "normal",
                    "allergies": ["Penicillin"]
                }
            )

    async def test_recommend_drugs_result_structure(self, mock_mcp_response, sample_drug_recommendations):
        """Test drug recommendations result structure."""
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_drug_recommendations)

            result = await client.recommend_drugs("P001", "Hypertension")

            assert "first_line_recommendations" in result
            assert "alternative_recommendations" in result
            assert "monitoring_parameters" in result
            assert "lifestyle_recommendations" in result

            first_line = result["first_line_recommendations"][0]
            assert "drug" in first_line
            assert "dosage" in first_line

    async def test_check_drug_interactions(self, mock_mcp_response):
        """Test drug interaction checking."""
        interactions = {
            "medications": ["Amlodipine", "Simvastatin"],
            "interactions": [
                {
                    "drugs": ["Amlodipine", "Simvastatin"],
                    "severity": "moderate",
                    "effect": "Increased simvastatin exposure",
                    "management": "Consider simvastatin dose reduction"
                }
            ],
            "severity_levels": ["moderate"]
        }
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(interactions)

            result = await client.check_drug_interactions(["Amlodipine", "Simvastatin"])

            assert len(result["interactions"]) > 0
            mock_call.assert_called_once_with(
                "check_drug_interactions",
                {"medications": ["Amlodipine", "Simvastatin"]}
            )

    async def test_check_drug_interactions_multiple(self, mock_mcp_response):
        """Test checking interactions for multiple medications."""
        interactions = {
            "medications": ["Warfarin", "Aspirin", "Lisinopril"],
            "interactions": [
                {
                    "drugs": ["Warfarin", "Aspirin"],
                    "severity": "moderate",
                    "effect": "Increased bleeding risk"
                }
            ]
        }
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(interactions)

            result = await client.check_drug_interactions(["Warfarin", "Aspirin", "Lisinopril"])

            assert len(result["medications"]) == 3

    async def test_check_contraindications(self, mock_mcp_response):
        """Test contraindication checking."""
        contraindications = {
            "medication": "Lisinopril",
            "absolute_contraindications": [
                "Angioedema related to previous ACE inhibitor therapy",
                "Hereditary or idiopathic angioedema"
            ],
            "relative_contraindications": [
                "Renal artery stenosis",
                "Pregnancy"
            ],
            "precautions": [
                "Monitor renal function",
                "Monitor potassium levels"
            ],
            "recommendations": "Avoid use in patients with history of angioedema"
        }
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(contraindications)

            result = await client.check_contraindications(
                "P001",
                "Lisinopril",
                conditions=["Pregnancy", "Renal artery stenosis"]
            )

            assert result["medication"] == "Lisinopril"
            assert len(result["absolute_contraindications"]) > 0
            mock_call.assert_called_once_with(
                "check_contraindications",
                {
                    "patient_id": "P001",
                    "medication": "Lisinopril",
                    "conditions": ["Pregnancy", "Renal artery stenosis"]
                }
            )

    async def test_check_medication_error_handling(self):
        """Test error handling for medication checking."""
        client = MedicationMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Medication service error")

            with pytest.raises(MCPToolError, match="Failed to check medication"):
                await client.check_medication("P001", "UnknownDrug")


# ========== ServiceMCPClient Tests ==========

@pytest.mark.asyncio
@pytest.mark.integration
class TestServiceMCPClient:
    """Test ServiceMCPClient (服务推荐)."""

    async def test_client_initialization(self):
        """Test ServiceMCPClient initialization."""
        client = ServiceMCPClient()
        assert client.server_name == "service_server"
        assert client.transport == "stdio"
        assert "service_server" in client.command

    async def test_recommend_insurance_basic(self, mock_mcp_response, sample_insurance_recommendations):
        """Test basic insurance recommendation."""
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_insurance_recommendations)

            result = await client.recommend_insurance("P001")

            assert "chronic_disease_insurance" in result
            assert "critical_illness_insurance" in result
            mock_call.assert_called_once_with(
                "recommend_insurance",
                {"patient_id": "P001", "budget_level": "medium"}
            )

    async def test_recommend_insurance_with_parameters(self, mock_mcp_response, sample_insurance_recommendations):
        """Test insurance recommendation with all parameters."""
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_insurance_recommendations)

            result = await client.recommend_insurance(
                "P001",
                diagnosis="Hypertension",
                risk_factors=["Obesity", "Family history"],
                age=45,
                budget_level="high"
            )

            assert "chronic_disease_insurance" in result
            mock_call.assert_called_once_with(
                "recommend_insurance",
                {
                    "patient_id": "P001",
                    "budget_level": "high",
                    "diagnosis": "Hypertension",
                    "risk_factors": ["Obesity", "Family history"],
                    "age": 45
                }
            )

    async def test_recommend_insurance_result_structure(self, mock_mcp_response, sample_insurance_recommendations):
        """Test insurance recommendation result structure."""
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_insurance_recommendations)

            result = await client.recommend_insurance("P001")

            assert "chronic_disease_insurance" in result
            assert "critical_illness_insurance" in result
            assert "medical_insurance" in result
            assert "coverage_details" in result

            insurance = result["chronic_disease_insurance"][0]
            assert "product_name" in insurance
            assert "coverage" in insurance
            assert "premium_estimate" in insurance

    async def test_recommend_health_services_basic(self, mock_mcp_response, sample_health_services):
        """Test basic health service recommendation."""
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_health_services)

            result = await client.recommend_health_services("P001")

            assert "disease_management_services" in result
            assert "preventive_services" in result
            mock_call.assert_called_once_with(
                "recommend_health_services",
                {"patient_id": "P001"}
            )

    async def test_recommend_health_services_with_condition(self, mock_mcp_response, sample_health_services):
        """Test health service recommendation with condition."""
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_health_services)

            result = await client.recommend_health_services(
                "P001",
                condition="Hypertension",
                health_goals=["Weight loss", "Blood pressure control"],
                service_type="management"
            )

            assert "disease_management_services" in result
            mock_call.assert_called_once_with(
                "recommend_health_services",
                {
                    "patient_id": "P001",
                    "condition": "Hypertension",
                    "health_goals": ["Weight loss", "Blood pressure control"],
                    "service_type": "management"
                }
            )

    async def test_recommend_health_services_result_structure(self, mock_mcp_response, sample_health_services):
        """Test health service result structure."""
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(sample_health_services)

            result = await client.recommend_health_services("P001")

            assert "disease_management_services" in result
            assert "health_promotion_services" in result
            assert "rehabilitation_services" in result
            assert "preventive_services" in result

            service = result["disease_management_services"][0]
            assert "service_name" in service
            assert "description" in service
            assert "price" in service

    async def test_recommend_checkup_packages(self, mock_mcp_response):
        """Test checkup package recommendations."""
        checkup_packages = {
            "basic_package": {
                "name": "Basic Health Checkup",
                "included_tests": ["Blood count", "Blood glucose", "Lipid panel"],
                "price": 500
            },
            "comprehensive_package": {
                "name": "Comprehensive Health Checkup",
                "included_tests": ["Blood count", "Blood glucose", "Lipid panel", "Thyroid", "Liver function"],
                "price": 1500
            },
            "targeted_packages": [
                {
                    "name": "Cardiovascular Checkup",
                    "included_tests": ["ECG", "Echocardiogram", "Stress test"],
                    "price": 800
                }
            ],
            "recommended_frequency": "Annually for adults over 40"
        }
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(checkup_packages)

            result = await client.recommend_checkup_packages(
                "P001",
                age_group="middle",
                risk_factors=["Hypertension", "Family history of heart disease"]
            )

            assert "basic_package" in result
            assert "comprehensive_package" in result
            mock_call.assert_called_once_with(
                "recommend_checkup_packages",
                {
                    "patient_id": "P001",
                    "age_group": "middle",
                    "risk_factors": ["Hypertension", "Family history of heart disease"]
                }
            )

    async def test_recommend_rehabilitation(self, mock_mcp_response):
        """Test rehabilitation recommendations."""
        rehabilitation = {
            "condition": "Stroke",
            "cardiac_rehabilitation": [],
            "pulmonary_rehabilitation": [],
            "physical_therapy": [
                {
                    "program": "Stroke Rehabilitation PT",
                    "duration": "8-12 weeks",
                    "frequency": "3 times per week"
                }
            ],
            "occupational_therapy": [
                {
                    "program": "Daily Living Skills Training",
                    "duration": "6-8 weeks"
                }
            ],
            "exercise_programs": [
                {
                    "name": "Range of Motion Exercises",
                    "description": "Daily exercises recommended"
                }
            ],
            "service_providers": ["Beijing Rehabilitation Hospital"],
            "expected_outcomes": ["Improved mobility", "Enhanced independence"]
        }
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(rehabilitation)

            result = await client.recommend_rehabilitation(
                "P001",
                "Stroke",
                recovery_stage="subacute"
            )

            assert result["condition"] == "Stroke"
            assert len(result["physical_therapy"]) > 0
            mock_call.assert_called_once_with(
                "recommend_rehabilitation",
                {
                    "patient_id": "P001",
                    "condition": "Stroke",
                    "recovery_stage": "subacute"
                }
            )

    async def test_recommend_insurance_error_handling(self):
        """Test error handling for insurance recommendation."""
        client = ServiceMCPClient()

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Service unavailable")

            with pytest.raises(MCPToolError, match="Failed to recommend insurance"):
                await client.recommend_insurance("P001")


# ========== MCPClientFactory Tests ==========

@pytest.mark.integration
class TestMCPClientFactory:
    """Test MCPClientFactory."""

    def test_get_profile_client(self):
        """Test getting profile client from factory."""
        client = MCPClientFactory.get_client("profile_server")
        assert isinstance(client, ProfileMCPClient)
        assert client.server_name == "profile_server"

    def test_get_triage_client(self):
        """Test getting triage client from factory."""
        client = MCPClientFactory.get_client("triage_server")
        assert isinstance(client, TriageMCPClient)
        assert client.server_name == "triage_server"

    def test_get_medication_client(self):
        """Test getting medication client from factory."""
        client = MCPClientFactory.get_client("medication_server")
        assert isinstance(client, MedicationMCPClient)
        assert client.server_name == "medication_server"

    def test_get_service_client(self):
        """Test getting service client from factory."""
        client = MCPClientFactory.get_client("service_server")
        assert isinstance(client, ServiceMCPClient)
        assert client.server_name == "service_server"

    def test_list_registered_servers(self):
        """Test listing all registered servers."""
        servers = MCPClientFactory.list_registered_servers()
        expected_servers = ["profile_server", "triage_server", "medication_server", "service_server"]
        assert set(servers) == set(expected_servers)

    def test_is_registered(self):
        """Test checking if a server is registered."""
        assert MCPClientFactory.is_registered("profile_server") is True
        assert MCPClientFactory.is_registered("triage_server") is True
        assert MCPClientFactory.is_registered("medication_server") is True
        assert MCPClientFactory.is_registered("service_server") is True
        assert MCPClientFactory.is_registered("unknown_server") is False

    def test_get_unregistered_server_raises_error(self):
        """Test that getting an unregistered server raises ValueError."""
        with pytest.raises(ValueError, match="No client registered for server"):
            MCPClientFactory.get_client("unknown_server")

    def test_register_custom_client(self):
        """Test registering a custom client."""
        # Create a custom client class
        class CustomMCPClient(ProfileMCPClient):
            pass

        # Register it
        MCPClientFactory.register_client("custom_server", CustomMCPClient)

        # Verify it's registered
        assert MCPClientFactory.is_registered("custom_server") is True

        # Get the client
        client = MCPClientFactory.get_client("custom_server")
        assert isinstance(client, CustomMCPClient)

        # Clean up
        MCPClientFactory.unregister_client("custom_server")
        assert MCPClientFactory.is_registered("custom_server") is False

    def test_unregister_client(self):
        """Test unregistering a client."""
        # First register a custom client
        class TempMCPClient(ProfileMCPClient):
            pass

        MCPClientFactory.register_client("temp_server", TempMCPClient)
        assert MCPClientFactory.is_registered("temp_server") is True

        # Unregister it
        MCPClientFactory.unregister_client("temp_server")
        assert MCPClientFactory.is_registered("temp_server") is False


# ========== Integration Test Scenarios ==========

@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPClientIntegrationScenarios:
    """Integration test scenarios combining multiple clients."""

    async def test_patient_journey_profile_to_triage(self, mock_mcp_response):
        """Test patient journey: get profile then get hospital recommendations."""
        profile_client = ProfileMCPClient()
        triage_client = TriageMCPClient()

        profile_data = {
            "patient_id": "P001",
            "name": "张三",
            "age": 55,
            "gender": "male",
            "location": "Beijing"
        }
        hospitals_data = {
            "hospitals": [
                {
                    "hospital_id": "H001",
                    "name": "北京协和医院",
                    "level": "tertiary",
                    "distance_km": 5.0
                }
            ]
        }

        with patch.object(profile_client, 'call_tool', new_callable=AsyncMock) as mock_profile:
            with patch.object(triage_client, 'call_tool', new_callable=AsyncMock) as mock_triage:
                mock_profile.return_value = mock_mcp_response(profile_data)
                mock_triage.return_value = mock_mcp_response(hospitals_data)

                # Get patient profile
                profile = await profile_client.get_patient_profile("P001")
                assert profile["patient_id"] == "P001"

                # Get hospital recommendations based on profile (returns list directly)
                hospitals = await triage_client.get_hospitals("P001", severity="moderate")
                assert len(hospitals) > 0
                assert isinstance(hospitals, list)

    async def test_medication_workflow(self, mock_mcp_response):
        """Test complete medication workflow: check, recommend, and check interactions."""
        medication_client = MedicationMCPClient()

        check_result = {
            "medication_name": "Amlodipine",
            "indication_match": True,
            "dosage_appropriate": True
        }
        recommend_result = {
            "condition": "Hypertension",
            "first_line_recommendations": [
                {"drug": "Amlodipine", "dosage": "5mg once daily"}
            ]
        }
        interaction_result = {
            "interactions": []
        }

        with patch.object(medication_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                mock_mcp_response(check_result),
                mock_mcp_response(recommend_result),
                mock_mcp_response(interaction_result)
            ]

            # Step 1: Check medication
            check = await medication_client.check_medication("P001", "Amlodipine")
            assert check["indication_match"] is True

            # Step 2: Get recommendations
            recommend = await medication_client.recommend_drugs("P001", "Hypertension")
            assert len(recommend["first_line_recommendations"]) > 0

            # Step 3: Check interactions
            interactions = await medication_client.check_drug_interactions(["Amlodipine"])
            assert "interactions" in interactions

    async def test_service_recommendation_workflow(self, mock_mcp_response):
        """Test service recommendation workflow: insurance and health services."""
        service_client = ServiceMCPClient()

        insurance_data = {
            "medical_insurance": [
                {"product_name": "Basic Medical", "premium": "500 CNY/year"}
            ]
        }
        health_services_data = {
            "disease_management_services": [
                {"service_name": "Hypertension Management", "price": "2000 CNY"}
            ]
        }
        checkup_data = {
            "basic_package": {"name": "Basic Checkup", "price": 500}
        }

        with patch.object(service_client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                mock_mcp_response(insurance_data),
                mock_mcp_response(health_services_data),
                mock_mcp_response(checkup_data)
            ]

            # Get insurance recommendations
            insurance = await service_client.recommend_insurance("P001")
            assert len(insurance["medical_insurance"]) > 0

            # Get health service recommendations
            services = await service_client.recommend_health_services("P001", condition="Hypertension")
            assert len(services["disease_management_services"]) > 0

            # Get checkup package recommendations
            checkup = await service_client.recommend_checkup_packages("P001")
            assert "basic_package" in checkup

    async def test_multi_client_parallel_usage(self, mock_mcp_response):
        """Test using multiple clients in parallel."""
        profile_client = ProfileMCPClient()
        triage_client = TriageMCPClient()
        medication_client = MedicationMCPClient()

        profile_data = {"patient_id": "P001", "name": "Test Patient"}
        hospitals_data = {"hospitals": [{"name": "Test Hospital"}]}
        medication_data = {"medication_name": "Test Drug", "safe": True}

        with patch.object(profile_client, 'call_tool', new_callable=AsyncMock) as mock_profile:
            with patch.object(triage_client, 'call_tool', new_callable=AsyncMock) as mock_triage:
                with patch.object(medication_client, 'call_tool', new_callable=AsyncMock) as mock_med:
                    mock_profile.return_value = mock_mcp_response(profile_data)
                    mock_triage.return_value = mock_mcp_response(hospitals_data)
                    mock_med.return_value = mock_mcp_response(medication_data)

                    # Run all calls in parallel
                    results = await asyncio.gather(
                        profile_client.get_patient_profile("P001"),
                        triage_client.get_hospitals("P001"),
                        medication_client.check_medication("P001", "Aspirin")
                    )

                    assert len(results) == 3
                    assert results[0]["patient_id"] == "P001"
                    # get_hospitals returns a list directly
                    assert isinstance(results[1], list)
                    assert results[2]["medication_name"] == "Test Drug"

    async def test_client_error_recovery(self, mock_mcp_response):
        """Test client behavior when errors occur."""
        client = ProfileMCPClient()

        # First call fails, second succeeds
        success_data = {"patient_id": "P001", "name": "Test Patient"}

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                Exception("Temporary failure"),
                mock_mcp_response(success_data)
            ]

            # First call fails
            with pytest.raises(MCPToolError):
                await client.get_patient_profile("P001")

            # Second call succeeds
            result = await client.get_patient_profile("P001")
            assert result["patient_id"] == "P001"


# ========== Edge Cases and Error Handling ==========

@pytest.mark.asyncio
@pytest.mark.integration
class TestMCPClientEdgeCases:
    """Test edge cases and error handling for MCP clients."""

    async def test_empty_response_handling(self):
        """Test handling of empty responses."""
        client = ProfileMCPClient()
        mock_result = Mock()
        mock_result.content = []

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result

            result = await client.get_patient_profile("P001")
            # When content is empty, _parse_tool_result returns {"raw": str(result)}
            assert "raw" in result

    async def test_malformed_json_response(self):
        """Test handling of malformed JSON in response."""
        client = ProfileMCPClient()
        mock_result = Mock()
        mock_content = Mock()
        mock_content.text = "{invalid json"
        mock_result.content = [mock_content]

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result

            result = await client.get_patient_profile("P001")
            assert "raw" in result

    async def test_special_characters_in_parameters(self, mock_mcp_response):
        """Test handling of special characters in parameters."""
        client = ProfileMCPClient()
        profile_data = {
            "patient_id": "P001",
            "name": "张三@#$%",
            "notes": "Special characters: <>&\"'"
        }

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(profile_data)

            result = await client.get_patient_profile("P001")
            assert result["name"] == "张三@#$%"

    async def test_large_parameter_list(self, mock_mcp_response):
        """Test handling of large parameter lists."""
        client = MedicationMCPClient()
        medications = [f"Medication_{i}" for i in range(100)]
        interaction_data = {"interactions": []}

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(interaction_data)

            result = await client.check_drug_interactions(medications)
            assert "interactions" in result

    async def test_unicode_data_handling(self, mock_mcp_response):
        """Test proper handling of Unicode data."""
        client = TriageMCPClient()
        hospitals_data = {
            "hospitals": [
                {
                    "name": "北京协和医院",
                    "address": "北京市东城区帅府园1号",
                    "description": "三级甲等综合医院"
                }
            ]
        }

        with patch.object(client, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_mcp_response(hospitals_data)

            result = await client.get_hospitals("P001")
            # get_hospitals returns a list directly
            hospital = result[0]
            assert hospital["name"] == "北京协和医院"
            assert hospital["address"] == "北京市东城区帅府园1号"
