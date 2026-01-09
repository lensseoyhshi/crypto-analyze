"""initial migration - create raw_api_responses table

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
	"""Create raw_api_responses table with indexes."""
	op.create_table(
		"raw_api_responses",
		sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
		sa.Column("source", sa.String(length=64), nullable=False, comment="API source (e.g., 'dexscreener', 'birdeye')"),
		sa.Column("endpoint", sa.String(length=256), nullable=False, comment="API endpoint path"),
		sa.Column("response_json", sa.Text(), nullable=False, comment="Raw JSON response as text"),
		sa.Column("status_code", sa.Integer(), nullable=False, default=200, comment="HTTP status code"),
		sa.Column("error_message", sa.Text(), nullable=True, comment="Error message if request failed"),
		sa.Column("created_at", sa.DateTime(), nullable=False, comment="Timestamp when response was saved"),
	)
	
	# Create indexes
	op.create_index("ix_raw_api_responses_id", "raw_api_responses", ["id"])
	op.create_index("ix_raw_api_responses_source", "raw_api_responses", ["source"])
	op.create_index("ix_raw_api_responses_created_at", "raw_api_responses", ["created_at"])
	op.create_index("idx_source_endpoint_created", "raw_api_responses", ["source", "endpoint", "created_at"])


def downgrade():
	"""Drop raw_api_responses table and all indexes."""
	op.drop_index("idx_source_endpoint_created", table_name="raw_api_responses")
	op.drop_index("ix_raw_api_responses_created_at", table_name="raw_api_responses")
	op.drop_index("ix_raw_api_responses_source", table_name="raw_api_responses")
	op.drop_index("ix_raw_api_responses_id", table_name="raw_api_responses")
	op.drop_table("raw_api_responses")


