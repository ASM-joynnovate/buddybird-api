from collections.abc import Sequence

from alembic import op

revision: str = "b5a24d1c8b64"
down_revision: str | Sequence[str] | None = "cf6067f31499"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA legacy")
    op.execute("ALTER TABLE public.word_entries SET SCHEMA legacy")
    op.execute("ALTER TABLE public.audio_captures SET SCHEMA legacy")
    op.execute("ALTER TABLE public.audio_segments SET SCHEMA legacy")
    op.execute("ALTER TABLE public.audio_capture_labels SET SCHEMA legacy")
    op.execute("ALTER TABLE public.label_categories SET SCHEMA legacy")
    op.execute("ALTER TABLE public.label_options SET SCHEMA legacy")


def downgrade() -> None:
    op.execute("ALTER TABLE legacy.label_options SET SCHEMA public")
    op.execute("ALTER TABLE legacy.label_categories SET SCHEMA public")
    op.execute("ALTER TABLE legacy.audio_capture_labels SET SCHEMA public")
    op.execute("ALTER TABLE legacy.audio_segments SET SCHEMA public")
    op.execute("ALTER TABLE legacy.audio_captures SET SCHEMA public")
    op.execute("ALTER TABLE legacy.word_entries SET SCHEMA public")
    op.execute("DROP SCHEMA legacy")
