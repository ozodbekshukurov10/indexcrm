import uuid

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class ActiveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        ordering = ("-created_at",)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=("deleted_at", "updated_at"))

    def restore(self, using=None):
        self.deleted_at = None
        self.save(using=using, update_fields=("deleted_at", "updated_at"))

    def delete(self, using=None, keep_parents=False):
        self.soft_delete(using=using, keep_parents=keep_parents)

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)
