from fastapi import FastAPI
from app.auth import router as auth_router
from fastapi import Depends
from app.auth import get_current_user
from app.models import User
from app.routers.items import router as items_router
from app.routers.comments import router as comments_router
from app.routers.acitivity import router as activity_router
from app.routers.teams import router as teams_router

app = FastAPI(
    title = "Newtonic Operations Api",
    version = "1.0.0"
)
app.include_router(auth_router)
app.include_router(items_router)
app.include_router(comments_router)
app.include_router(activity_router)
app.include_router(teams_router)

@app.get("/")
def home():
    return {"message": "welcome to newtonic operations api"}



@app.get("/health")
def health():
    return {"status": "healthy"}   



@app.get("/me")
def get_my_profile(current_user :User = Depends(get_current_user)):
    return{
        "id":current_user.id,
        "name":current_user.name,
        "email":current_user.email
    }
