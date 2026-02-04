from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from core.security import verify_password, create_access_token, hash_password
from schemas.auth import TokenOut, LoginIn, UserCreate
from db import get_db
from models.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    email = _normalize_email(data.email)

    u = db.query(User).filter(User.email == email).first()
    if not u or not u.is_active:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not verify_password(data.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token(sub=str(u.id), extra={"role": u.role})
    return TokenOut(access_token=token, token_type="bearer")


@router.post("/register", status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    email = _normalize_email(user_in.email)

    # valida duplicidade
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Esse email já foi cadastrado")

    # valida phone duplicado
    if hasattr(User, "phone") and db.query(User).filter(User.phone == user_in.phone).first():
        raise HTTPException(status_code=400, detail="Esse telefone já foi cadastrado")

    # cria usuário
    u = User(
        name=user_in.name,
        email=email,
        phone=user_in.phone,
        password_hash=hash_password(user_in.password),
        is_active=True,
        role="user",  # ou UserRole.user se for Enum
        # brand_id=...  # se estiver em multi-tenant, isso deve vir do slug/header, não do body
    )

    db.add(u)
    db.commit()
    db.refresh(u)

    return {"id": str(u.id), "email": u.email}
