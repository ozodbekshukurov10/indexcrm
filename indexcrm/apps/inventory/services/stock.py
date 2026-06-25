from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models import Product
from apps.inventory.models import Stock, StockMovement, StockMovementType, Warehouse


class StockService:
    @staticmethod
    def _to_decimal(quantity):
        try:
            value = Decimal(str(quantity))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError(
                {"quantity": "Quantity must be a valid decimal."}
            ) from error

        if value <= Decimal("0.000"):
            raise ValidationError({"quantity": "Quantity must be greater than zero."})

        return value

    @staticmethod
    def _get_locked_stock(warehouse: Warehouse, product: Product) -> Stock:
        stock = (
            Stock.objects.select_for_update()
            .filter(warehouse=warehouse, product=product)
            .first()
        )
        if stock:
            return stock

        return Stock.objects.create(warehouse=warehouse, product=product)

    @staticmethod
    def _create_movement(
        *,
        warehouse: Warehouse,
        product: Product,
        movement_type: str,
        quantity: Decimal,
        created_by,
        expiry_date=None,
        note: str = "",
    ) -> StockMovement:
        movement = StockMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            expiry_date=expiry_date,
            created_by=(
                created_by if getattr(created_by, "is_authenticated", False) else None
            ),
            note=note,
        )
        from apps.accounts.models import AuditAction
        from apps.accounts.services import record_audit_log

        record_audit_log(
            actor=created_by,
            action=AuditAction.STOCK,
            entity_type="inventory.StockMovement",
            entity_id=movement.id,
            object_repr=f"{product.name} {movement_type}",
            summary=note or f"{movement_type} stock movement created.",
            metadata={
                "warehouse_id": str(warehouse.id),
                "product_id": str(product.id),
                "quantity": str(quantity),
                "movement_type": movement_type,
            },
        )
        return movement

    @classmethod
    @transaction.atomic
    def increase_stock(
        cls,
        *,
        warehouse: Warehouse,
        product: Product,
        quantity,
        created_by=None,
        expiry_date=None,
        note: str = "",
        movement_type: str = StockMovementType.IN,
    ) -> StockMovement:
        quantity = cls._to_decimal(quantity)
        stock = cls._get_locked_stock(warehouse, product)
        stock.quantity += quantity
        stock.full_clean()
        stock.save(update_fields=("quantity", "updated_at"))

        return cls._create_movement(
            warehouse=warehouse,
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            expiry_date=expiry_date,
            created_by=created_by,
            note=note,
        )

    @classmethod
    @transaction.atomic
    def decrease_stock(
        cls,
        *,
        warehouse: Warehouse,
        product: Product,
        quantity,
        created_by=None,
        expiry_date=None,
        note: str = "",
        movement_type: str = StockMovementType.OUT,
    ) -> StockMovement:
        quantity = cls._to_decimal(quantity)
        stock = cls._get_locked_stock(warehouse, product)

        if stock.quantity - quantity < Decimal("0.000"):
            raise ValidationError({"quantity": "Stock cannot become negative."})
        if stock.quantity - quantity < stock.reserved_quantity:
            raise ValidationError(
                {"quantity": "Stock cannot be reduced below reserved quantity."}
            )

        stock.quantity -= quantity
        stock.full_clean()
        stock.save(update_fields=("quantity", "updated_at"))

        return cls._create_movement(
            warehouse=warehouse,
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            expiry_date=expiry_date,
            created_by=created_by,
            note=note,
        )

    @classmethod
    @transaction.atomic
    def transfer_stock(
        cls,
        *,
        source_warehouse: Warehouse,
        target_warehouse: Warehouse,
        product: Product,
        quantity,
        created_by=None,
        expiry_date=None,
        note: str = "",
    ) -> StockMovement:
        if source_warehouse.pk == target_warehouse.pk:
            raise ValidationError(
                {"target_warehouse": "Target warehouse must be different."}
            )

        outbound = cls.decrease_stock(
            warehouse=source_warehouse,
            product=product,
            quantity=quantity,
            created_by=created_by,
            expiry_date=expiry_date,
            note=note,
            movement_type=StockMovementType.TRANSFER,
        )
        cls.increase_stock(
            warehouse=target_warehouse,
            product=product,
            quantity=quantity,
            created_by=created_by,
            expiry_date=expiry_date,
            note=note,
            movement_type=StockMovementType.TRANSFER,
        )

        return outbound

    @classmethod
    @transaction.atomic
    def adjust_stock(
        cls,
        *,
        warehouse: Warehouse,
        product: Product,
        target_quantity,
        created_by=None,
        expiry_date=None,
        note: str = "",
    ) -> StockMovement:
        try:
            target_quantity = Decimal(str(target_quantity))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError(
                {"quantity": "Quantity must be a valid decimal."}
            ) from error

        if target_quantity < Decimal("0.000"):
            raise ValidationError({"quantity": "Stock cannot become negative."})

        stock = cls._get_locked_stock(warehouse, product)
        changed_quantity = abs(target_quantity - stock.quantity)
        if changed_quantity == Decimal("0.000"):
            raise ValidationError(
                {"quantity": "Adjustment matches the current stock quantity."}
            )
        if target_quantity < stock.reserved_quantity:
            raise ValidationError(
                {"quantity": "Adjusted stock cannot be below reserved quantity."}
            )

        stock.quantity = target_quantity
        stock.full_clean()
        stock.save(update_fields=("quantity", "updated_at"))

        return cls._create_movement(
            warehouse=warehouse,
            product=product,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity=changed_quantity,
            expiry_date=expiry_date,
            created_by=created_by,
            note=note,
        )

    @classmethod
    def apply_movement(
        cls,
        *,
        warehouse: Warehouse,
        product: Product,
        movement_type: str,
        quantity,
        created_by=None,
        expiry_date=None,
        note: str = "",
        target_warehouse: Warehouse | None = None,
    ) -> StockMovement:
        if movement_type == StockMovementType.IN:
            return cls.increase_stock(
                warehouse=warehouse,
                product=product,
                quantity=quantity,
                created_by=created_by,
                expiry_date=expiry_date,
                note=note,
            )
        if movement_type == StockMovementType.OUT:
            return cls.decrease_stock(
                warehouse=warehouse,
                product=product,
                quantity=quantity,
                created_by=created_by,
                expiry_date=expiry_date,
                note=note,
            )
        if movement_type == StockMovementType.TRANSFER:
            if target_warehouse is None:
                raise ValidationError(
                    {"target_warehouse": "Target warehouse is required."}
                )
            return cls.transfer_stock(
                source_warehouse=warehouse,
                target_warehouse=target_warehouse,
                product=product,
                quantity=quantity,
                created_by=created_by,
                expiry_date=expiry_date,
                note=note,
            )
        if movement_type == StockMovementType.ADJUSTMENT:
            return cls.adjust_stock(
                warehouse=warehouse,
                product=product,
                target_quantity=quantity,
                created_by=created_by,
                expiry_date=expiry_date,
                note=note,
            )

        raise ValidationError({"movement_type": "Unsupported stock movement type."})
