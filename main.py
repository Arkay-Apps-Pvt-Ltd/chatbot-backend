from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.auth import router as auth_route
from app.api.v1.message import router as message_route
from app.api.v1.tags import router as tag_route
from app.api.v1.contact import router as contact_route
from app.api.v1.webhook import router as webhook_route
from dependency import get_current_user

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_route, prefix="/v1")
app.include_router(tag_route, prefix="/v1", dependencies=[Depends(get_current_user)])
app.include_router(contact_route, prefix="/v1", dependencies=[Depends(get_current_user)])
app.include_router(message_route, prefix="/v1", dependencies=[Depends(get_current_user)])
app.include_router(webhook_route)