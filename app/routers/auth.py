from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from core.security import verify_password, create_access_token, hash_password
from schemas.auth import TokenOut

router = APIRouter()

# Usuário fake (trocar por DB depois)
FAKE_USER = {
    "id": "1",
    "email": "admin@teste.com",
    "password_hash": hash_password("123456"),
    "brand_id": "brand_demo",  # já preparando multi-tenant
    "role": "admin",
}

@router.post("/token", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm manda username + password
    #trata username como email
    if form.username.lower() != FAKE_USER["email"]:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not verify_password(form.password, FAKE_USER["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token(
        sub=FAKE_USER["id"],
        extra={
            "email": FAKE_USER["email"],
            "brand_id": FAKE_USER["brand_id"],
            "role": FAKE_USER["role"],
        },
    )
    return TokenOut(access_token=token)
