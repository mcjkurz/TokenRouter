"""User registration API endpoints."""
import secrets
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.database import Team
from app.models.schemas import RegistrationRequest, RegistrationResponse

router = APIRouter(prefix="/register", tags=["registration"])


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def validate_email(email: str) -> bool:
    """Validate email format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format.
    Returns (is_valid, error_message).
    """
    # Check for spaces
    if ' ' in username:
        return False, "Username cannot contain spaces"
    
    # Check alphanumeric (allows underscores)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username must contain only letters, numbers, and underscores"
    
    return True, ""


@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    registration_data: RegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Requirements:
    - Username must be unique and 3-50 characters
    - Email must be valid and from an allowed domain
    - Access code must match the server configuration
    
    Returns:
    - API key (save it, you won't see it again!)
    - Account details with default quota
    """
    # Check if registration is enabled
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is currently disabled"
        )
    
    # Validate access code
    if not settings.registration_access_codes_list:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration access codes not configured on server"
        )
    
    if not settings.is_registration_access_code_valid(registration_data.access_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access code"
        )
    
    # Validate username format (extra layer of validation beyond Pydantic)
    username_valid, username_error = validate_username(registration_data.username)
    if not username_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=username_error
        )
    
    # Validate email format
    if not validate_email(registration_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Validate email domain
    if not settings.is_email_domain_allowed(registration_data.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email domain not allowed"
        )
    
    # Check if username already exists
    existing_team = db.query(Team).filter(Team.name == registration_data.username).first()
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{registration_data.username}' is already taken"
        )
    
    # Check if email already exists
    existing_email = db.query(Team).filter(Team.email == registration_data.email.lower()).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{registration_data.email}' already exists"
        )
    
    # Generate API key
    api_key = generate_token()
    
    # Ensure token is unique (very unlikely collision, but check anyway)
    existing_token = db.query(Team).filter(Team.token == api_key).first()
    if existing_token:
        # Generate a new one if collision (extremely rare)
        api_key = generate_token()
    
    # Create the team/account with local time for created_at
    team = Team(
        name=registration_data.username,
        email=registration_data.email.lower(),  # Store email in lowercase for consistency
        token=api_key,
        quota_tokens=settings.default_registration_quota,
        max_requests_per_minute=60,  # Default rate limit
        used_tokens=0,
        is_active=True,
        created_at=datetime.now()  # Use local time
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Prepare API base URL and usage example
    api_base_url = settings.public_api_url if settings.public_api_url else None
    usage_example = None
    if api_base_url:
        usage_example = f"""from openai import OpenAI

client = OpenAI(
    api_key="{api_key}",
    base_url="{api_base_url}"
)

response = client.chat.completions.create(
    model="{settings.default_model}",
    messages=[{{"role": "user", "content": "Hello!"}}]
)

content = response.choices[0].message.content
print(content)"""
    
    return RegistrationResponse(
        message="Account created successfully!",
        username=registration_data.username,
        email=registration_data.email,
        api_key=api_key,
        api_base_url=api_base_url,
        quota_tokens=settings.default_registration_quota,
        warning="⚠️ IMPORTANT: Save this API key now! You won't be able to see it again.",
        usage_example=usage_example
    )

