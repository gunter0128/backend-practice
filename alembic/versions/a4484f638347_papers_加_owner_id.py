"""papers 加 owner_id

Revision ID: a4484f638347
Revises: d9c5dbe0f7d0
Create Date: 2026-09-04 10:59:19.159055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4484f638347'
down_revision: Union[str, Sequence[str], None] = 'd9c5dbe0f7d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 只加欄位；外鍵約束在 SQLite 不強制、batch mode 又要求命名，先略過。
    # Project 1 用 Postgres 時再用命名慣例正式處理。
    with op.batch_alter_table('papers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('papers', schema=None) as batch_op:
        batch_op.drop_column('owner_id')
