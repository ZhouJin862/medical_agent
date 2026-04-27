"""add rules tables

Revision ID: 002_add_rules
Revises: 001_initial_schema_with_seed_data
Create Date: 2024-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '002_add_rules'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create rules table
    op.create_table(
        'rules',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(50), nullable=False, server_default='threshold'),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('target_type', sa.String(50), nullable=False, server_default='vital_sign'),
        sa.Column('rule_config', sa.JSON(), nullable=False),
        sa.Column('disease_code', sa.String(50), nullable=True, index=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('change_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # Create rule_execution_history table
    op.create_table(
        'rule_execution_history',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('rule_id', sa.CHAR(36), nullable=False, index=True),
        sa.Column('patient_id', sa.String(100), nullable=False, index=True),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('matched', sa.Boolean(), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('consultation_id', sa.String(100), nullable=True),
        sa.Column('skill_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # Create vital_sign_standards table
    op.create_table(
        'vital_sign_standards',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('vital_sign_type', sa.String(50), nullable=False),
        sa.Column('normal_min', sa.Float(), nullable=True),
        sa.Column('normal_max', sa.Float(), nullable=True),
        sa.Column('low_risk_min', sa.Float(), nullable=True),
        sa.Column('low_risk_max', sa.Float(), nullable=True),
        sa.Column('medium_risk_min', sa.Float(), nullable=True),
        sa.Column('medium_risk_max', sa.Float(), nullable=True),
        sa.Column('high_risk_min', sa.Float(), nullable=True),
        sa.Column('high_risk_max', sa.Float(), nullable=True),
        sa.Column('very_high_risk_min', sa.Float(), nullable=True),
        sa.Column('very_high_risk_max', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('gender_specific', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('age_adjustments', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # Create risk_score_rules table
    op.create_table(
        'risk_score_rules',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('disease_code', sa.String(50), nullable=False, index=True),
        sa.Column('scoring_config', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # Insert default vital sign standards
    op.execute("""
        INSERT INTO vital_sign_standards (id, name, display_name, vital_sign_type, normal_min, normal_max, high_risk_min, very_high_risk_min, unit, enabled) VALUES
        (UUID(), 'systolic_bp', '收缩压', 'blood_pressure', 90, 140, 140, 160, 'mmHg', 1),
        (UUID(), 'diastolic_bp', '舒张压', 'blood_pressure', 60, 90, 90, 100, 'mmHg', 1),
        (UUID(), 'fasting_glucose', '空腹血糖', 'blood_glucose', 3.9, 6.1, 7.0, 11.1, 'mmol/L', 1),
        (UUID(), 'bmi', '体重指数', 'bmi', 18.5, 24.0, 28.0, 32.0, 'kg/m²', 1),
        (UUID(), 'total_cholesterol', '总胆固醇', 'lipid_profile', 0, 5.2, 6.2, 7.2, 'mmol/L', 1),
        (UUID(), 'ldl_cholesterol', '低密度脂蛋白', 'lipid_profile', 0, 3.4, 4.1, 4.9, 'mmol/L', 1),
        (UUID(), 'hdl_cholesterol', '高密度脂蛋白', 'lipid_profile', 0.9, NULL, NULL, NULL, 'mmol/L', 1),
        (UUID(), 'triglycerides', '甘油三酯', 'lipid_profile', 0, 1.7, 2.3, 5.6, 'mmol/L', 1),
        (UUID(), 'uric_acid', '尿酸', 'uric_acid', 0, 420, 480, 540, 'μmol/L', 1)
    """)

    # Insert default hypertension risk score rule
    op.execute("""
        INSERT INTO risk_score_rules (id, name, display_name, description, disease_code, scoring_config, enabled) VALUES
        (UUID(), 'hypertension_risk_score', '高血压风险评分', '根据血压、年龄、家族史等因素评估高血压风险', 'hypertension',
        '{
            "factors": [
                {"name": "systolic_bp", "weight": 0.35, "type": "range", "min": 120, "max": 180},
                {"name": "diastolic_bp", "weight": 0.35, "type": "range", "min": 80, "max": 110},
                {"name": "age", "weight": 0.2, "type": "range", "min": 18, "max": 80},
                {"name": "family_history", "weight": 0.1, "type": "binary"}
            ],
            "thresholds": {"low": 0.25, "medium": 0.45, "high": 0.65, "very_high": 0.8}
        }', 1)
    """)

    # Insert default diabetes risk score rule
    op.execute("""
        INSERT INTO risk_score_rules (id, name, display_name, description, disease_code, scoring_config, enabled) VALUES
        (UUID(), 'diabetes_risk_score', '糖尿病风险评分', '根据血糖、BMI、年龄等因素评估糖尿病风险', 'diabetes',
        '{
            "factors": [
                {"name": "fasting_glucose", "weight": 0.35, "type": "range", "min": 4.0, "max": 12.0},
                {"name": "bmi", "weight": 0.3, "type": "range", "min": 18, "max": 35},
                {"name": "age", "weight": 0.2, "type": "range", "min": 18, "max": 80},
                {"name": "family_history", "weight": 0.15, "type": "binary"}
            ],
            "thresholds": {"low": 0.2, "medium": 0.4, "high": 0.6, "very_high": 0.8}
        }', 1)
    """)


def downgrade() -> None:
    op.drop_table('risk_score_rules')
    op.drop_table('vital_sign_standards')
    op.drop_table('rule_execution_history')
    op.drop_table('rules')
