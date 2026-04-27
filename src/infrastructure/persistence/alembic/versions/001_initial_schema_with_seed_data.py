# pylint: skip-file
"""
Initial schema migration with seed data.

Creates all tables for the medical agent system including:
- consultations and messages
- health_plans and prescriptions
- skills, skill_prompts, skill_model_configs
- disease_types
- knowledge_bases
- vital_signs_standards

Also seeds initial data for disease_types and vital_signs_standards.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import json

# revision identifiers, used by Alembic
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables and insert seed data."""

    # ============================================
    # Create disease_types table first (other tables reference it)
    # ============================================
    op.create_table(
        "disease_types",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
            comment="Primary key",
        ),
        sa.Column(
            "code",
            sa.String(50),
            nullable=False,
            comment="Disease code (HYPERTENSION, DIABETES, etc.)",
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Disease name in Chinese",
        ),
        sa.Column(
            "name_en",
            sa.String(100),
            nullable=False,
            comment="Disease name in English",
        ),
        sa.Column(
            "category",
            sa.Enum("four_highs", "obesity", name="diseasecategory"),
            nullable=False,
            comment="Disease category",
        ),
        sa.Column(
            "icd_code",
            sa.String(20),
            nullable=True,
            comment="ICD-10 code",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Disease description",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Disease types for four-highs and obesity",
    )

    op.create_index(
        "idx_disease_type_code",
        "disease_types",
        ["code"],
        unique=True,
    )

    # ============================================
    # Insert seed data for disease_types (四高一重)
    # ============================================
    from uuid import uuid4

    disease_types_table = table(
        "disease_types",
        column("id", sa.CHAR(36)),
        column("code", sa.String(50)),
        column("name", sa.String(100)),
        column("name_en", sa.String(100)),
        column("category", sa.String(50)),
        column("icd_code", sa.String(20)),
        column("description", sa.Text()),
    )

    now = sa.text("CURRENT_TIMESTAMP")

    # Four Highs (四高)
    op.bulk_insert(
        disease_types_table,
        [
            {
                "id": uuid4().hex,
                "code": "HYPERTENSION",
                "name": "高血压",
                "name_en": "Hypertension",
                "category": "four_highs",
                "icd_code": "I10",
                "description": "动脉血压持续升高的慢性疾病，是心血管疾病的主要危险因素",
            },
            {
                "id": uuid4().hex,
                "code": "DIABETES",
                "name": "糖尿病",
                "name_en": "Diabetes Mellitus",
                "category": "four_highs",
                "icd_code": "E11",
                "description": "以血糖升高为特征的代谢性疾病，分为1型和2型",
            },
            {
                "id": uuid4().hex,
                "code": "DYSLIPIDEMIA",
                "name": "血脂异常",
                "name_en": "Dyslipidemia",
                "category": "four_highs",
                "icd_code": "E78",
                "description": "血液中脂质水平异常，包括高胆固醇、高甘油三酯等",
            },
            {
                "id": uuid4().hex,
                "code": "GOUT",
                "name": "痛风",
                "name_en": "Gout",
                "category": "four_highs",
                "icd_code": "M10",
                "description": "尿酸代谢紊乱导致的关节炎，可伴肾损害",
            },
            # Obesity (一重)
            {
                "id": uuid4().hex,
                "code": "OBESITY",
                "name": "肥胖",
                "name_en": "Obesity",
                "category": "obesity",
                "icd_code": "E66",
                "description": "体内脂肪堆积过多，BMI≥28为中国成人肥胖标准",
            },
        ],
    )

    # ============================================
    # Create vital_signs_standards table
    # ============================================
    op.create_table(
        "vital_signs_standards",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "indicator_code",
            sa.String(50),
            nullable=False,
            comment="Indicator code (SBP, DBP, FPG, HbA1c, TC, TG, LDL_C, UA, BMI)",
        ),
        sa.Column(
            "indicator_name",
            sa.String(100),
            nullable=False,
            comment="Indicator name",
        ),
        sa.Column(
            "disease_code",
            sa.String(50),
            nullable=True,
            comment="Associated disease code",
        ),
        sa.Column(
            "unit",
            sa.String(20),
            nullable=False,
            comment="Unit of measurement",
        ),
        sa.Column(
            "normal_min",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Normal range minimum",
        ),
        sa.Column(
            "normal_max",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Normal range maximum",
        ),
        sa.Column(
            "risk_low_min",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Low risk range minimum",
        ),
        sa.Column(
            "risk_low_max",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Low risk range maximum",
        ),
        sa.Column(
            "risk_medium_min",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Medium risk range minimum",
        ),
        sa.Column(
            "risk_medium_max",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Medium risk range maximum",
        ),
        sa.Column(
            "risk_high_min",
            sa.Numeric(10, 2),
            nullable=True,
            comment="High risk range minimum",
        ),
        sa.Column(
            "risk_high_max",
            sa.Numeric(10, 2),
            nullable=True,
            comment="High risk range maximum",
        ),
        sa.Column(
            "gender",
            sa.String(10),
            nullable=True,
            comment="Gender specific (male/female/both)",
        ),
        sa.Column(
            "age_min",
            sa.Integer(),
            nullable=True,
            comment="Minimum age for this standard",
        ),
        sa.Column(
            "age_max",
            sa.Integer(),
            nullable=True,
            comment="Maximum age for this standard",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Description of the standard",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Reference ranges for vital signs indicators",
    )

    op.create_index(
        "idx_vital_signs_indicator",
        "vital_signs_standards",
        ["indicator_code"],
        unique=True,
    )
    op.create_index(
        "idx_vital_signs_disease",
        "vital_signs_standards",
        ["disease_code"],
    )

    # ============================================
    # Insert seed data for vital_signs_standards
    # ============================================
    vital_signs_table = table(
        "vital_signs_standards",
        column("id", sa.CHAR(36)),
        column("indicator_code", sa.String(50)),
        column("indicator_name", sa.String(100)),
        column("disease_code", sa.String(50)),
        column("unit", sa.String(20)),
        column("normal_min", sa.Numeric(10, 2)),
        column("normal_max", sa.Numeric(10, 2)),
        column("risk_low_min", sa.Numeric(10, 2)),
        column("risk_low_max", sa.Numeric(10, 2)),
        column("risk_medium_min", sa.Numeric(10, 2)),
        column("risk_medium_max", sa.Numeric(10, 2)),
        column("risk_high_min", sa.Numeric(10, 2)),
        column("risk_high_max", sa.Numeric(10, 2)),
        column("gender", sa.String(10)),
        column("age_min", sa.Integer()),
        column("age_max", sa.Integer()),
        column("description", sa.Text()),
    )

    op.bulk_insert(
        vital_signs_table,
        [
            # Blood Pressure - SBP (收缩压)
            {
                "id": uuid4().hex,
                "indicator_code": "SBP",
                "indicator_name": "收缩压",
                "disease_code": "HYPERTENSION",
                "unit": "mmHg",
                "normal_min": 90,
                "normal_max": 120,
                "risk_low_min": 120,
                "risk_low_max": 140,
                "risk_medium_min": 140,
                "risk_medium_max": 160,
                "risk_high_min": 160,
                "risk_high_max": 300,
                "gender": None,
                "age_min": 18,
                "age_max": None,
                "description": "收缩压正常值<120mmHg，正常高值120-139mmHg，高血压≥140mmHg",
            },
            # Blood Pressure - DBP (舒张压)
            {
                "id": uuid4().hex,
                "indicator_code": "DBP",
                "indicator_name": "舒张压",
                "disease_code": "HYPERTENSION",
                "unit": "mmHg",
                "normal_min": 60,
                "normal_max": 80,
                "risk_low_min": 80,
                "risk_low_max": 90,
                "risk_medium_min": 90,
                "risk_medium_max": 100,
                "risk_high_min": 100,
                "risk_high_max": 200,
                "gender": None,
                "age_min": 18,
                "age_max": None,
                "description": "舒张压正常值<80mmHg，正常高值80-89mmHg，高血压≥90mmHg",
            },
            # FPG - Fasting Plasma Glucose (空腹血糖)
            {
                "id": uuid4().hex,
                "indicator_code": "FPG",
                "indicator_name": "空腹血糖",
                "disease_code": "DIABETES",
                "unit": "mmol/L",
                "normal_min": 3.9,
                "normal_max": 6.1,
                "risk_low_min": 6.1,
                "risk_low_max": 7.0,
                "risk_medium_min": 7.0,
                "risk_medium_max": 11.1,
                "risk_high_min": 11.1,
                "risk_high_max": 30,
                "gender": None,
                "age_min": None,
                "age_max": None,
                "description": "空腹血糖正常<6.1mmol/L，空腹血糖受损6.1-7.0mmol/L，糖尿病≥7.0mmol/L",
            },
            # HbA1c - Glycated Hemoglobin (糖化血红蛋白)
            {
                "id": uuid4().hex,
                "indicator_code": "HbA1c",
                "indicator_name": "糖化血红蛋白",
                "disease_code": "DIABETES",
                "unit": "%",
                "normal_min": 4,
                "normal_max": 6,
                "risk_low_min": 6,
                "risk_low_max": 6.5,
                "risk_medium_min": 6.5,
                "risk_medium_max": 8,
                "risk_high_min": 8,
                "risk_high_max": 15,
                "gender": None,
                "age_min": None,
                "age_max": None,
                "description": "HbA1c正常<6%，糖尿病前期6-6.5%，糖尿病≥6.5%",
            },
            # TC - Total Cholesterol (总胆固醇)
            {
                "id": uuid4().hex,
                "indicator_code": "TC",
                "indicator_name": "总胆固醇",
                "disease_code": "DYSLIPIDEMIA",
                "unit": "mmol/L",
                "normal_min": None,
                "normal_max": 5.2,
                "risk_low_min": 5.2,
                "risk_low_max": 6.2,
                "risk_medium_min": 6.2,
                "risk_medium_max": 7.2,
                "risk_high_min": 7.2,
                "risk_high_max": 20,
                "gender": None,
                "age_min": None,
                "age_max": None,
                "description": "总胆固醇合适水平<5.2mmol/L，边缘升高5.2-6.2mmol/L，升高≥6.2mmol/L",
            },
            # TG - Triglycerides (甘油三酯)
            {
                "id": uuid4().hex,
                "indicator_code": "TG",
                "indicator_name": "甘油三酯",
                "disease_code": "DYSLIPIDEMIA",
                "unit": "mmol/L",
                "normal_min": None,
                "normal_max": 1.7,
                "risk_low_min": 1.7,
                "risk_low_max": 2.3,
                "risk_medium_min": 2.3,
                "risk_medium_max": 5.6,
                "risk_high_min": 5.6,
                "risk_high_max": 20,
                "gender": None,
                "age_min": None,
                "age_max": None,
                "description": "甘油三酯合适水平<1.7mmol/L，边缘升高1.7-2.3mmol/L，升高≥2.3mmol/L",
            },
            # LDL-C - Low Density Lipoprotein Cholesterol (低密度脂蛋白胆固醇)
            {
                "id": uuid4().hex,
                "indicator_code": "LDL_C",
                "indicator_name": "低密度脂蛋白胆固醇",
                "disease_code": "DYSLIPIDEMIA",
                "unit": "mmol/L",
                "normal_min": None,
                "normal_max": 3.4,
                "risk_low_min": 3.4,
                "risk_low_max": 4.1,
                "risk_medium_min": 4.1,
                "risk_medium_max": 4.9,
                "risk_high_min": 4.9,
                "risk_high_max": 15,
                "gender": None,
                "age_min": None,
                "age_max": None,
                "description": "LDL-C合适水平<3.4mmol/L，边缘升高3.4-4.1mmol/L，升高≥4.1mmol/L",
            },
            # UA - Uric Acid (血尿酸)
            {
                "id": uuid4().hex,
                "indicator_code": "UA",
                "indicator_name": "血尿酸",
                "disease_code": "GOUT",
                "unit": "μmol/L",
                "normal_min": None,
                "normal_max": 420,
                "risk_low_min": 420,
                "risk_low_max": 480,
                "risk_medium_min": 480,
                "risk_medium_max": 540,
                "risk_high_min": 540,
                "risk_high_max": 1000,
                "gender": None,
                "age_min": None,
                "age_max": None,
                "description": "血尿酸正常<420μmol/L，高尿酸血症≥420μmol/L",
            },
            # BMI - Body Mass Index (体质指数)
            {
                "id": uuid4().hex,
                "indicator_code": "BMI",
                "indicator_name": "体质指数",
                "disease_code": "OBESITY",
                "unit": "kg/m²",
                "normal_min": 18.5,
                "normal_max": 24,
                "risk_low_min": 24,
                "risk_low_max": 28,
                "risk_medium_min": 28,
                "risk_medium_max": 32,
                "risk_high_min": 32,
                "risk_high_max": 60,
                "gender": None,
                "age_min": 18,
                "age_max": None,
                "description": "BMI正常18.5-24，超重24-28，肥胖≥28（中国标准）",
            },
        ],
    )

    # ============================================
    # Create consultations table
    # ============================================
    op.create_table(
        "consultations",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "consultation_id",
            sa.CHAR(36),
            nullable=False,
            comment="Unique consultation identifier",
        ),
        sa.Column(
            "patient_id",
            sa.CHAR(36),
            nullable=False,
            comment="Patient identifier",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "archived", name="consultationstatus"),
            nullable=False,
            default="active",
            comment="Consultation status",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Consultation sessions between patients and AI assistant",
    )

    op.create_index(
        "ix_consultations_consultation_id",
        "consultations",
        ["consultation_id"],
        unique=True,
    )
    op.create_index(
        "ix_consultations_patient_id",
        "consultations",
        ["patient_id"],
    )
    op.create_index(
        "ix_consultations_status",
        "consultations",
        ["status"],
    )
    op.create_index(
        "idx_consultation_patient_status",
        "consultations",
        ["patient_id", "status"],
    )

    # ============================================
    # Create messages table
    # ============================================
    op.create_table(
        "messages",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "consultation_id",
            sa.CHAR(36),
            sa.ForeignKey(
                "consultations.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            comment="Reference to consultation",
        ),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="messagerole"),
            nullable=False,
            comment="Message sender role",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Message content",
        ),
        sa.Column(
            "intent",
            sa.String(100),
            nullable=True,
            comment="Classified intent",
        ),
        sa.Column(
            "structured_metadata",
            sa.JSON(),
            nullable=True,
            comment="Structured data from AI response",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Messages in consultation conversations",
    )

    op.create_index(
        "ix_messages_consultation_id",
        "messages",
        ["consultation_id"],
    )
    op.create_index(
        "ix_messages_intent",
        "messages",
        ["intent"],
    )
    op.create_index(
        "idx_message_consultation_created",
        "messages",
        ["consultation_id", "created_at"],
    )

    # ============================================
    # Create health_plans table
    # ============================================
    op.create_table(
        "health_plans",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "plan_id",
            sa.CHAR(36),
            nullable=False,
            unique=True,
            comment="Unique plan identifier",
        ),
        sa.Column(
            "patient_id",
            sa.CHAR(36),
            nullable=False,
            comment="Patient identifier",
        ),
        sa.Column(
            "plan_type",
            sa.Enum(
                "comprehensive",
                "disease_specific",
                name="healthplantype",
            ),
            nullable=False,
            default="comprehensive",
            comment="Type of health plan",
        ),
        sa.Column(
            "disease_code",
            sa.String(50),
            nullable=True,
            comment="Associated disease code",
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=True,
            comment="Plan title",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Plan description",
        ),
        sa.Column(
            "valid_from",
            sa.String(50),
            nullable=True,
            comment="Valid from date",
        ),
        sa.Column(
            "valid_until",
            sa.String(50),
            nullable=True,
            comment="Valid until date",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Health management plans for patients",
    )

    op.create_index(
        "ix_health_plans_plan_id",
        "health_plans",
        ["plan_id"],
        unique=True,
    )
    op.create_index(
        "ix_health_plans_patient_id",
        "health_plans",
        ["patient_id"],
    )
    op.create_index(
        "ix_health_plans_disease_code",
        "health_plans",
        ["disease_code"],
    )

    # ============================================
    # Create prescriptions table
    # ============================================
    op.create_table(
        "prescriptions",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "health_plan_id",
            sa.CHAR(36),
            sa.ForeignKey(
                "health_plans.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            comment="Reference to health plan",
        ),
        sa.Column(
            "prescription_type",
            sa.Enum(
                "diet",
                "exercise",
                "sleep",
                "medication",
                "psych",
                name="prescriptiontype",
            ),
            nullable=False,
            comment="Type of prescription",
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
            comment="Prescription title",
        ),
        sa.Column(
            "content",
            sa.JSON(),
            nullable=False,
            comment="Prescription content",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=True,
            comment="Priority level",
        ),
        sa.Column(
            "frequency",
            sa.String(50),
            nullable=True,
            comment="Execution frequency",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Additional notes",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Prescriptions within health plans",
    )

    op.create_index(
        "ix_prescriptions_health_plan_id",
        "prescriptions",
        ["health_plan_id"],
    )
    op.create_index(
        "idx_prescription_plan_type",
        "prescriptions",
        ["health_plan_id", "prescription_type"],
    )

    # ============================================
    # Create skills table
    # ============================================
    op.create_table(
        "skills",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            unique=True,
            comment="Skill name (e.g., hypertension_assessment)",
        ),
        sa.Column(
            "display_name",
            sa.String(255),
            nullable=False,
            comment="Display name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Skill description",
        ),
        sa.Column(
            "type",
            sa.Enum(
                "generic",
                "disease_specific",
                "prescription",
                "mcp_tool",
                name="skilltype",
            ),
            nullable=False,
            comment="Skill type",
        ),
        sa.Column(
            "category",
            sa.Enum(
                "health_assessment",
                "risk_prediction",
                "health_promotion",
                "prescription_generation",
                "triage_guidance",
                "medication_check",
                "service_recommendation",
                name="skillcategory",
            ),
            nullable=True,
            comment="Skill category",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            default=True,
            comment="Is skill enabled",
        ),
        sa.Column(
            "version",
            sa.String(20),
            nullable=False,
            default="1.0.0",
            comment="Skill version",
        ),
        sa.Column(
            "intent_keywords",
            sa.JSON(),
            nullable=True,
            comment="Intent keywords for routing",
        ),
        sa.Column(
            "config",
            sa.JSON(),
            nullable=True,
            comment="Additional configuration",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Configurable AI skills",
    )

    op.create_index(
        "ix_skills_name",
        "skills",
        ["name"],
        unique=True,
    )
    op.create_index(
        "ix_skills_type",
        "skills",
        ["type"],
    )
    op.create_index(
        "ix_skills_enabled",
        "skills",
        ["enabled"],
    )
    op.create_index(
        "idx_skill_type_enabled",
        "skills",
        ["type", "enabled"],
    )

    # ============================================
    # Create skill_prompts table
    # ============================================
    op.create_table(
        "skill_prompts",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            sa.CHAR(36),
            sa.ForeignKey(
                "skills.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            comment="Reference to skill",
        ),
        sa.Column(
            "prompt_type",
            sa.String(50),
            nullable=False,
            comment="Prompt type (system, user, output)",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Prompt content",
        ),
        sa.Column(
            "version",
            sa.String(20),
            nullable=False,
            default="1.0.0",
            comment="Prompt version",
        ),
        sa.Column(
            "variables",
            sa.JSON(),
            nullable=True,
            comment="Template variables",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Prompt templates for skills",
    )

    op.create_index(
        "ix_skill_prompts_skill_id",
        "skill_prompts",
        ["skill_id"],
    )
    op.create_index(
        "idx_skill_prompt_skill_type",
        "skill_prompts",
        ["skill_id", "prompt_type"],
    )

    # ============================================
    # Create skill_model_configs table
    # ============================================
    op.create_table(
        "skill_model_configs",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            sa.CHAR(36),
            sa.ForeignKey(
                "skills.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            unique=True,
            comment="Reference to skill",
        ),
        sa.Column(
            "model_provider",
            sa.Enum(
                "internal",
                "openai",
                "anthropic",
                "azure",
                name="modelprovider",
            ),
            nullable=False,
            default="internal",
            comment="LLM provider",
        ),
        sa.Column(
            "model_name",
            sa.String(100),
            nullable=False,
            comment="Model name",
        ),
        sa.Column(
            "temperature",
            sa.Numeric(3, 2),
            nullable=True,
            comment="Temperature setting",
        ),
        sa.Column(
            "max_tokens",
            sa.Integer(),
            nullable=True,
            comment="Max tokens",
        ),
        sa.Column(
            "top_p",
            sa.Numeric(3, 2),
            nullable=True,
            comment="Top P setting",
        ),
        sa.Column(
            "config",
            sa.JSON(),
            nullable=True,
            comment="Additional config",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Model configuration for skills",
    )

    op.create_index(
        "ix_skill_model_configs_skill_id",
        "skill_model_configs",
        ["skill_id"],
        unique=True,
    )

    # ============================================
    # Create knowledge_bases table
    # ============================================
    op.create_table(
        "knowledge_bases",
        sa.Column(
            "id",
            sa.CHAR(36),
            primary_key=True,
        ),
        sa.Column(
            "code",
            sa.String(100),
            nullable=False,
            unique=True,
            comment="Knowledge base code",
        ),
        sa.Column(
            "disease_code",
            sa.String(50),
            sa.ForeignKey("disease_types.code"),
            nullable=True,
            comment="Associated disease code",
        ),
        sa.Column(
            "knowledge_type",
            sa.Enum(
                "guideline",
                "risk_rule",
                "reference",
                "drug_guide",
                "care_standard",
                name="knowledgetype",
            ),
            nullable=False,
            comment="Type of knowledge",
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
            comment="Knowledge title",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Knowledge content",
        ),
        sa.Column(
            "source",
            sa.String(255),
            nullable=False,
            comment="Source of knowledge",
        ),
        sa.Column(
            "version",
            sa.String(20),
            nullable=False,
            default="1.0.0",
            comment="Knowledge version",
        ),
        sa.Column(
            "effective_date",
            sa.String(50),
            nullable=True,
            comment="Effective date",
        ),
        sa.Column(
            "tags",
            sa.JSON(),
            nullable=True,
            comment="Tags for indexing",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Medical knowledge and guidelines",
    )

    op.create_index(
        "ix_knowledge_bases_code",
        "knowledge_bases",
        ["code"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_bases_disease_code",
        "knowledge_bases",
        ["disease_code"],
    )
    op.create_index(
        "idx_knowledge_disease_type",
        "knowledge_bases",
        ["disease_code", "knowledge_type"],
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""

    op.drop_index("idx_knowledge_disease_type", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_disease_code", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_code", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")

    op.drop_index("ix_skill_model_configs_skill_id", table_name="skill_model_configs")
    op.drop_table("skill_model_configs")

    op.drop_index("idx_skill_prompt_skill_type", table_name="skill_prompts")
    op.drop_index("ix_skill_prompts_skill_id", table_name="skill_prompts")
    op.drop_table("skill_prompts")

    op.drop_index("idx_skill_type_enabled", table_name="skills")
    op.drop_index("ix_skills_enabled", table_name="skills")
    op.drop_index("ix_skills_type", table_name="skills")
    op.drop_index("ix_skills_name", table_name="skills")
    op.drop_table("skills")

    op.drop_index("idx_prescription_plan_type", table_name="prescriptions")
    op.drop_index("ix_prescriptions_health_plan_id", table_name="prescriptions")
    op.drop_table("prescriptions")

    op.drop_index("ix_health_plans_disease_code", table_name="health_plans")
    op.drop_index("ix_health_plans_patient_id", table_name="health_plans")
    op.drop_index("ix_health_plans_plan_id", table_name="health_plans")
    op.drop_table("health_plans")

    op.drop_index("idx_message_consultation_created", table_name="messages")
    op.drop_index("ix_messages_intent", table_name="messages")
    op.drop_index("ix_messages_consultation_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("idx_consultation_patient_status", table_name="consultations")
    op.drop_index("ix_consultations_status", table_name="consultations")
    op.drop_index("ix_consultations_patient_id", table_name="consultations")
    op.drop_index("ix_consultations_consultation_id", table_name="consultations")
    op.drop_table("consultations")

    op.drop_index("idx_vital_signs_disease", table_name="vital_signs_standards")
    op.drop_index("idx_vital_signs_indicator", table_name="vital_signs_standards")
    op.drop_table("vital_signs_standards")

    op.drop_index("idx_disease_type_code", table_name="disease_types")
    op.drop_table("disease_types")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS knowledgetype")
    op.execute("DROP TYPE IF EXISTS modelprovider")
    op.execute("DROP TYPE IF EXISTS skillcategory")
    op.execute("DROP TYPE IF EXISTS skilltype")
    op.execute("DROP TYPE IF EXISTS prescriptiontype")
    op.execute("DROP TYPE IF EXISTS healthplantype")
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.execute("DROP TYPE IF EXISTS consultationstatus")
    op.execute("DROP TYPE IF EXISTS diseasecategory")
