"""Update application activity audit log schema."""

from alembic import op
import sqlalchemy as sa

revision = "1f6c79e39c5b"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    with op.batch_alter_table(
        "admin_audit_logs",
        recreate="always",
    ) as batch_op:

        # Allow activities without an authenticated user.
        batch_op.alter_column(
            "actor_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

        batch_op.alter_column(
            "target_user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

        # Add the activity category.
        batch_op.add_column(
            sa.Column(
                "category",
                sa.String(),
                nullable=False,
                server_default="GENERAL",
            )
        )

        # Add the operation result.
        batch_op.add_column(
            sa.Column(
                "result",
                sa.String(),
                nullable=False,
                server_default="SUCCESS",
            )
        )

        # Add request source information.
        batch_op.add_column(
            sa.Column(
                "ip_address",
                sa.String(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "user_agent",
                sa.String(),
                nullable=True,
            )
        )

    # Create indexes for filtering audit records.
    op.create_index(
        "ix_admin_audit_logs_category",
        "admin_audit_logs",
        ["category"],
    )

    op.create_index(
        "ix_admin_audit_logs_result",
        "admin_audit_logs",
        ["result"],
    )


def downgrade():
    op.drop_index(
        "ix_admin_audit_logs_result",
        table_name="admin_audit_logs",
    )

    op.drop_index(
        "ix_admin_audit_logs_category",
        table_name="admin_audit_logs",
    )

    with op.batch_alter_table(
        "admin_audit_logs",
        recreate="always",
    ) as batch_op:

        batch_op.drop_column("user_agent")
        batch_op.drop_column("ip_address")
        batch_op.drop_column("result")
        batch_op.drop_column("category")

        batch_op.alter_column(
            "actor_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

        batch_op.alter_column(
            "target_user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )