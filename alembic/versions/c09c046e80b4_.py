"""initial schema with all tables

Revision ID: c09c046e80b4
Revises:
Create Date: 2026-08-14 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c09c046e80b4"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoice_batches",
        sa.Column("cycle_index", sa.Integer(), nullable=False),
        sa.Column("invoice_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_batches_id"), "invoice_batches", ["id"], unique=False)

    op.create_table(
        "invoice_records",
        sa.Column("stark_invoice_id", sa.String(), nullable=True),
        sa.Column("batch_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("tax_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["invoice_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_records_id"), "invoice_records", ["id"], unique=False)
    op.create_index(
        op.f("ix_invoice_records_stark_invoice_id"),
        "invoice_records",
        ["stark_invoice_id"],
        unique=False,
    )

    op.create_table(
        "schedule_cycles",
        sa.Column("cycle_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_count", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedule_cycles_id"), "schedule_cycles", ["id"], unique=False)
    op.create_index(
        op.f("ix_schedule_cycles_cycle_index"),
        "schedule_cycles",
        ["cycle_index"],
        unique=False,
    )

    op.create_table(
        "scheduler_state",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("is_paused", sa.Boolean(), nullable=False),
        sa.Column("last_scheduled_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduler_state_id"), "scheduler_state", ["id"], unique=False)
    op.create_index(op.f("ix_scheduler_state_key"), "scheduler_state", ["key"], unique=True)

    op.create_table(
        "transfer_records",
        sa.Column("stark_transfer_id", sa.String(), nullable=True),
        sa.Column("stark_invoice_id", sa.String(), nullable=True),
        sa.Column("event_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("fee", sa.Integer(), nullable=False),
        sa.Column("net_amount", sa.Integer(), nullable=False),
        sa.Column("target_bank_code", sa.String(), nullable=False),
        sa.Column("target_branch", sa.String(), nullable=False),
        sa.Column("target_account", sa.String(), nullable=False),
        sa.Column("target_name", sa.String(), nullable=False),
        sa.Column("target_tax_id", sa.String(), nullable=False),
        sa.Column("target_account_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transfer_records_id"), "transfer_records", ["id"], unique=False)
    op.create_index(
        op.f("ix_transfer_records_event_id"),
        "transfer_records",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transfer_records_stark_invoice_id"),
        "transfer_records",
        ["stark_invoice_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transfer_records_stark_transfer_id"),
        "transfer_records",
        ["stark_transfer_id"],
        unique=False,
    )

    op.create_table(
        "webhook_events",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("subscription", sa.String(), nullable=True),
        sa.Column("log_type", sa.String(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_events_id"), "webhook_events", ["id"], unique=False)
    op.create_index(
        op.f("ix_webhook_events_event_id"),
        "webhook_events",
        ["event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("transfer_records")
    op.drop_table("scheduler_state")
    op.drop_table("schedule_cycles")
    op.drop_table("invoice_records")
    op.drop_table("invoice_batches")
