import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, LargeBinary, Boolean, DateTime, func, Integer, Uuid
from .db import Base

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)

    phone_e164_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phone_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True, index=True)

    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, server_default=func.false(), nullable=False)
    twofa_phone_verified: Mapped[bool] = mapped_column(Boolean, server_default=func.false(), nullable=False)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
