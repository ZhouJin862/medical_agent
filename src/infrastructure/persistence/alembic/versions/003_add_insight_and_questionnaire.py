"""add insight and questionnaire tables

Revision ID: 003_add_insight_and_questionnaire
Revises: 002_add_rules
Create Date: 2025-04-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '003_add_insight_and_questionnaire'
down_revision = '002_add_rules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create assessment_insights table
    op.create_table(
        'assessment_insights',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('updated_by', sa.String(100), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=False, server_default=func.current_timestamp()),
        sa.Column('updated_date', sa.DateTime(), nullable=False, server_default=func.current_timestamp()),
        sa.Column('party_id', sa.String(64), nullable=False, index=True),
        sa.Column('skill_name', sa.String(128), nullable=False),
        sa.Column('risk_level', sa.String(32), nullable=False, server_default=''),
        sa.Column('population_classification', sa.JSON(), nullable=True),
        sa.Column('abnormal_indicators', sa.JSON(), nullable=True),
        sa.Column('recommended_data_collection', sa.JSON(), nullable=True),
        sa.Column('disease_prediction', sa.JSON(), nullable=True),
        sa.Column('intervention_prescriptions', sa.JSON(), nullable=True),
        sa.Column('full_result', sa.JSON(), nullable=True),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # Create questionnaires table
    op.create_table(
        'questionnaires',
        sa.Column('id', sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('updated_by', sa.String(100), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=False, server_default=func.current_timestamp()),
        sa.Column('updated_date', sa.DateTime(), nullable=False, server_default=func.current_timestamp()),
        sa.Column('questionnaire_id', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('skill_name', sa.String(128), nullable=True),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )


def downgrade() -> None:
    op.drop_table('questionnaires')
    op.drop_table('assessment_insights')
