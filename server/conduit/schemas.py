from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_password_change: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class SetupRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    is_bot: bool = False


class CreateUserResponse(BaseModel):
    id: int
    username: str
    is_bot: bool
    api_token: str | None = None  # Only for bots; shown once


class UserResponse(BaseModel):
    id: int
    username: str
    is_bot: bool
    uses_default_password: bool | None = None  # Only for humans


class CreateDmRequest(BaseModel):
    target_username: str


class CreateRoomRequest(BaseModel):
    name: str


class UpdateRoomRequest(BaseModel):
    name: str | None = None


class UpdateMembersRequest(BaseModel):
    add: list[str] | None = None
    remove: list[str] | None = None


class SendMessageRequest(BaseModel):
    content: str
