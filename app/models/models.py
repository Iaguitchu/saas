import enum
import uuid
from datetime import datetime, date
from sqlalchemy import (
    String, DateTime, Boolean, ForeignKey, Integer, Text,
    UniqueConstraint, Index, Enum, Numeric, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.utcnow()


# -------------------------
# Enums
# -------------------------
class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    user = "user"
    pro = "pro"
    admin = "admin"


class SubscriptionStatus(str, enum.Enum):
    free = "free"
    active = "active"
    canceled = "canceled"
    past_due = "past_due"
    expired = "expired"


class PhotoType(str, enum.Enum):
    front = "front"
    back = "back"
    side_left = "side_left"
    side_right = "side_right"


# -------------------------
# Core SaaS (Brand / Plan)
# -------------------------
class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)  # p/ subdomínio ou rota
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # tema/cores (white-label básico)
    primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    users = relationship("User", back_populates="brand")
    plans = relationship("Plan", back_populates="brand")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # integrações externas (kirvano/hotmart/kiwifi)
    external_product_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    brand = relationship("Brand", back_populates="plans")
    users = relationship("User", back_populates="plan")

    __table_args__ = (
        Index("ix_plans_brand", "brand_id"),
    )


# -------------------------
# Users
# -------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True, index=True,)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)  # ideal E.164: +551199...

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.user)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # desafio e upsell WhatsApp IA
    challenge_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    whatsapp_ai_active_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # assinatura final
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.free
    )
    plan_valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # id externo do gateway (kirvano/hotmart)
    external_customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    brand = relationship("Brand", back_populates="users")
    plan = relationship("Plan", back_populates="users")

    # relações do produto
    assessments = relationship("UserAssessment", back_populates="user")
    photos = relationship("UserPhoto", back_populates="user")
    water_logs = relationship("WaterLog", back_populates="user")
    workout_sessions = relationship("WorkoutSession", back_populates="user")

    # atribuições profissional<->usuário (N:N)
    professionals = relationship(
        "User",
        secondary="professional_user",
        primaryjoin="User.id==ProfessionalUser.user_id",
        secondaryjoin="User.id==ProfessionalUser.professional_id",
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint("brand_id", "email", name="uq_users_brand_email"),
        UniqueConstraint("brand_id", "phone", name="uq_users_brand_phone"),
        Index("ix_users_brand", "brand_id"),
        Index("ix_users_role", "role"),
    )


# -------------------------
# Profissional <-> Usuário (atribuição)
# professional_id e user_id são ambos users.id (role pro vs user)
# -------------------------
class ProfessionalUser(Base):
    __tablename__ = "professional_user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)

    professional_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("professional_id", "user_id", name="uq_prof_user_pair"),
        Index("ix_prof_user_brand", "brand_id"),
        Index("ix_prof_user_professional", "professional_id"),
        Index("ix_prof_user_user", "user_id"),
    )


# -------------------------
# Anamnese (estruturada)
# -------------------------
class UserAssessment(Base):
    __tablename__ = "user_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Você pode ir estruturando com colunas depois.
    # Para MVP, JSON resolve sem travar você.
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="assessments")

    __table_args__ = (
        Index("ix_assess_brand_user", "brand_id", "user_id"),
    )


# -------------------------
# Fotos (armazenadas em blob/storage e aqui só URL + metadata)
# -------------------------
class UserPhoto(Base):
    __tablename__ = "user_photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    photo_type: Mapped[PhotoType] = mapped_column(Enum(PhotoType), nullable=False)
    url: Mapped[str] = mapped_column(String(800), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="photos")

    __table_args__ = (
        Index("ix_photos_brand_user", "brand_id", "user_id"),
        Index("ix_photos_user_type", "user_id", "photo_type"),
    )


# -------------------------
# Treinos padrão (templates)
# -------------------------
class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    exercises = relationship("WorkoutExercise", back_populates="workout_template", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_workout_templates_brand", "brand_id"),
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_templates.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reps: Mapped[str | None] = mapped_column(String(50), nullable=True)      # "10-12" ou "12"
    load: Mapped[str | None] = mapped_column(String(50), nullable=True)      # "20kg" ou "moderado"
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    workout_template = relationship("WorkoutTemplate", back_populates="exercises")

    __table_args__ = (
        Index("ix_workout_exercises_template", "workout_template_id"),
    )


# -------------------------
# Execução do treino (sessão) + marcação de exercícios
# -------------------------
class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    workout_template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_templates.id"), nullable=False)

    session_date: Mapped[date] = mapped_column(nullable=False, default=date.today)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="workout_sessions")
    items = relationship("WorkoutSessionItem", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "workout_template_id", "session_date", name="uq_session_unique_day"),
        Index("ix_sessions_brand_user_date", "brand_id", "user_id", "session_date"),
    )


class WorkoutSessionItem(Base):
    __tablename__ = "workout_session_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_sessions.id"), nullable=False)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workout_exercises.id"), nullable=False)

    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session = relationship("WorkoutSession", back_populates="items")

    __table_args__ = (
        UniqueConstraint("session_id", "exercise_id", name="uq_session_exercise"),
        Index("ix_session_items_session", "session_id"),
    )


# -------------------------
# Água (log diário)
# -------------------------
class WaterLog(Base):
    __tablename__ = "water_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    log_date: Mapped[date] = mapped_column(nullable=False, default=date.today)
    ml: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="water_logs")

    __table_args__ = (
        UniqueConstraint("user_id", "log_date", name="uq_water_user_day"),
        Index("ix_water_brand_user_date", "brand_id", "user_id", "log_date"),
    )


# -------------------------
# Webhook events (auditoria)
# -------------------------
class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)

    provider: Mapped[str] = mapped_column(String(40), nullable=False)   # kirvano/hotmart/kiwifi
    event_type: Mapped[str] = mapped_column(String(80), nullable=False) # payment.approved, subscription.renewed...
    external_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_webhook_brand_provider", "brand_id", "provider"),
        Index("ix_webhook_event_type", "event_type"),
    )