from django.utils.text import slugify


def build_unique_slug(instance, source_field="name", slug_field="slug"):
    source_value = getattr(instance, source_field, "")
    slug_field_object = instance._meta.get_field(slug_field)
    max_length = slug_field_object.max_length
    base_slug = slugify(source_value)[:max_length].strip("-") or "item"
    slug = base_slug
    suffix = 2

    manager = getattr(instance.__class__, "all_objects", instance.__class__.objects)
    queryset = manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(**{slug_field: slug}).exists():
        suffix_text = f"-{suffix}"
        slug = f"{base_slug[: max_length - len(suffix_text)]}{suffix_text}"
        suffix += 1

    return slug
