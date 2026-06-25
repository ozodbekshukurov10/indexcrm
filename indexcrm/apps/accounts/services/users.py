from dataclasses import dataclass

from apps.accounts.models import User


@dataclass(frozen=True)
class CreateUserPayload:
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    phone: str = ""


class UserService:
    @staticmethod
    def create_user(payload: CreateUserPayload) -> User:
        return User.objects.create_user(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
        )

    @staticmethod
    def update_profile(user: User, **fields) -> User:
        allowed_fields = {"first_name", "last_name", "phone"}
        changed_fields = []

        for field_name, value in fields.items():
            if field_name in allowed_fields:
                setattr(user, field_name, value)
                changed_fields.append(field_name)

        if changed_fields:
            user.save(update_fields=[*changed_fields, "updated_at"])

        return user
