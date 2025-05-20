from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_route
from app.api.message import router as message_route
from app.api.tags import router as tag_route
from app.api.contact import router as contact_route
from app.api.webhook import router as webhook_route
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

app.include_router(auth_route)
app.include_router(tag_route, dependencies=[Depends(get_current_user)])
app.include_router(contact_route, dependencies=[Depends(get_current_user)])
app.include_router(message_route, dependencies=[Depends(get_current_user)])
app.include_router(webhook_route)