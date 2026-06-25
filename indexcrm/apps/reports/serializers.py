from django.utils import timezone
from rest_framework import serializers


class BranchQuerySerializer(serializers.Serializer):
    branch = serializers.UUIDField(required=False)


class DateRangeQuerySerializer(BranchQuerySerializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "End date cannot be before start date."}
            )
        return attrs


class DailyReportQuerySerializer(BranchQuerySerializer):
    day = serializers.DateField(required=False, default=timezone.localdate)


class MonthlyReportQuerySerializer(BranchQuerySerializer):
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)


class InventoryReportQuerySerializer(BranchQuerySerializer):
    warehouse = serializers.UUIDField(required=False)
    category = serializers.UUIDField(required=False)
    brand = serializers.UUIDField(required=False)


class LowStockReportQuerySerializer(BranchQuerySerializer):
    warehouse = serializers.UUIDField(required=False)


class LimitDateRangeQuerySerializer(DateRangeQuerySerializer):
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=100, default=10
    )


class ExportQuerySerializer(MonthlyReportQuerySerializer):
    pass
