from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import BaseModel


class Store(BaseModel):
    name = models.CharField(max_length=255, help_text="Public store name.")
    logo = models.ImageField(
        upload_to="stores/logos/",
        blank=True,
        null=True,
        help_text="Store logo image.",
    )
    phone = models.CharField(
        max_length=32, blank=True, help_text="Primary store phone number."
    )
    address = models.TextField(blank=True, help_text="Main store address.")
    is_active = models.BooleanField(
        default=True, help_text="Whether the store is active."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stores",
        help_text="User who owns this store.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["owner", "is_active"]),
        ]

    def __str__(self):
        return self.name


class Branch(BaseModel):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="branches",
        help_text="Store this branch belongs to.",
    )
    name = models.CharField(max_length=255, help_text="Branch name.")
    address = models.TextField(blank=True, help_text="Branch address.")
    phone = models.CharField(
        max_length=32, blank=True, help_text="Branch phone number."
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_branches",
        help_text="Manager responsible for the branch.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the branch is active."
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_branch_name_per_store",
            )
        ]

    def __str__(self):
        return f"{self.store.name} - {self.name}"


class CashDesk(BaseModel):
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="cash_desks",
        help_text="Branch where this cash desk operates.",
    )
    name = models.CharField(max_length=255, help_text="Cash desk display name.")
    code = models.CharField(
        max_length=64, help_text="Unique cash desk code inside the branch."
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the cash desk is active."
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["code"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_cashdesk_code_per_branch",
            )
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.name}"
