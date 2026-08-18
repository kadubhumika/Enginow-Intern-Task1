from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import Base, engine, get_db
from app import models, schemas, auth, cache

Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Management & Authentication API")

@app.post("/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=auth.hash_password(user.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == credentials.username).first()
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = auth.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token)


# ---------- USER ROUTES (protected) ----------

@app.get("/users", response_model=schemas.UserListOut)
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    cache_key = f"users:page={page}:limit={limit}"
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    total = db.query(models.User).count()
    users = (
        db.query(models.User)
        .order_by(models.User.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    result = schemas.UserListOut(total=total, page=page, limit=limit, users=users)
    cache.cache_set(cache_key, result)
    return result


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    updates: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if updates.email is not None:
        user.email = updates.email
    if updates.password is not None:
        user.hashed_password = auth.hash_password(updates.password)

    db.commit()
    db.refresh(user)
    cache.cache_clear()  # invalidate stale list-cache after a change
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own account")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    cache.cache_clear()
    return None


@app.get("/")
def root():
    return {"message": "User Management API is running"}
