from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from django.utils import timezone

from apps.reports.selectors import (
    best_selling_products,
    cashbox_summaries,
    customer_debts_report,
    daily_sales_summary,
    expenses_report,
    inventory_report,
    low_stock_report,
    month_bounds,
    monthly_sales_summary,
    profit_report,
    recent_sales_report,
    supplier_debts_report,
    total_debt_summary,
)


def dashboard_summary(day=None, branch=None):
    day = day or timezone.localdate()
    today_sales = daily_sales_summary(day=day, branch=branch)
    today_profit = profit_report(date_from=day, date_to=day, branch=branch)
    expenses = expenses_report(date_from=day, date_to=day, branch=branch)
    low_stock = low_stock_report(branch=branch)
    return {
        "date": day,
        "today_sales": today_sales,
        "today_profit": today_profit,
        "total_expenses": expenses["total_expenses"],
        "total_debt": total_debt_summary(),
        "low_stock_count": low_stock["low_stock_count"],
        "best_selling_products": best_selling_products(
            date_from=day,
            date_to=day,
            branch=branch,
            limit=5,
        ),
        "recent_sales": recent_sales_report(limit=10, branch=branch),
        "cashbox_summary": cashbox_summaries(branch=branch),
    }


def _cell_reference(row_index, column_index):
    letters = ""
    while column_index:
        column_index, remainder = divmod(column_index - 1, 26)
        letters = chr(65 + remainder) + letters
    return f"{letters}{row_index}"


def _cell_xml(row_index, column_index, value):
    reference = _cell_reference(row_index, column_index)
    if value is None:
        return f'<c r="{reference}"/>'
    if isinstance(value, UUID):
        value = str(value)
    if isinstance(value, datetime):
        value = timezone.localtime(value).replace(tzinfo=None).isoformat(sep=" ")
    elif isinstance(value, date):
        value = value.isoformat()
    if isinstance(value, Decimal):
        return f'<c r="{reference}"><v>{value}</v></c>'
    if isinstance(value, int | float):
        return f'<c r="{reference}"><v>{value}</v></c>'
    text = escape(str(value))
    return f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>'


def _worksheet_xml(rows):
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            _cell_xml(row_index, column_index, value)
            for column_index, value in enumerate(row, start=1)
        )
        xml_rows.append(f'<row r="{row_index}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(xml_rows)}</sheetData>"
        "</worksheet>"
    )


def _safe_sheet_name(name, used_names):
    safe_name = "".join("_" if char in r"[]:*?/\\" else char for char in name)[:31]
    safe_name = safe_name or "Sheet"
    original = safe_name
    counter = 1
    while safe_name in used_names:
        suffix = f" {counter}"
        safe_name = f"{original[: 31 - len(suffix)]}{suffix}"
        counter += 1
    used_names.add(safe_name)
    return safe_name


def build_xlsx_workbook(sheets):
    used_names = set()
    sheet_items = [
        (_safe_sheet_name(name, used_names), rows or [["No data"]])
        for name, rows in sheets.items()
    ]
    workbook_sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _rows) in enumerate(sheet_items, start=1)
    )
    workbook_relationships = "".join(
        (
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
        for index, _sheet in enumerate(sheet_items, start=1)
    )
    overrides = "".join(
        (
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
        for index, _sheet in enumerate(sheet_items, start=1)
    )

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                f"{overrides}</Types>"
            ),
        )
        workbook.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
        )
        workbook.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f"<sheets>{workbook_sheets}</sheets></workbook>"
            ),
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f"{workbook_relationships}</Relationships>"
            ),
        )
        for index, (_name, rows) in enumerate(sheet_items, start=1):
            workbook.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows))
    return output.getvalue()


def monthly_sales_export(year=None, month=None, branch=None):
    report = monthly_sales_summary(year=year, month=month, branch=branch)
    rows = [
        ["Metric", "Value"],
        ["Date from", report["date_from"]],
        ["Date to", report["date_to"]],
        ["Total sales", report["total_sales"]],
        ["Gross sales", report["gross_sales"]],
        ["Refund amount", report["refund_amount"]],
        ["Net sales", report["net_sales"]],
        ["Paid amount", report["paid_amount"]],
        ["Debt amount", report["debt_amount"]],
    ]
    daily_rows = [["Day", "Sale count", "Total amount", "Paid amount", "Debt amount"]]
    daily_rows.extend(
        [
            row["day"],
            row["sale_count"],
            row["total_amount"],
            row["paid_amount"],
            row["debt_amount"],
        ]
        for row in report["daily"]
    )
    filename = f"monthly-sales-{report['date_from']:%Y-%m}.xlsx"
    return filename, build_xlsx_workbook({"Summary": rows, "Daily": daily_rows})


def monthly_profit_export(year=None, month=None, branch=None):
    date_from, date_to = month_bounds(year, month)
    report = profit_report(date_from=date_from, date_to=date_to, branch=branch)
    rows = [["Metric", "Value"], ["Date from", date_from], ["Date to", date_to]]
    rows.extend([key, value] for key, value in report.items())
    filename = f"monthly-profit-{date_from:%Y-%m}.xlsx"
    return filename, build_xlsx_workbook({"Profit": rows})


def inventory_export(branch=None, warehouse=None, category=None, brand=None):
    report = inventory_report(
        branch=branch,
        warehouse=warehouse,
        category=category,
        brand=brand,
    )
    summary_rows = [["Metric", "Value"]]
    summary_rows.extend([key, value] for key, value in report.items() if key != "items")
    item_rows = [
        [
            "Branch",
            "Warehouse",
            "Product",
            "SKU",
            "Category",
            "Brand",
            "Quantity",
            "Reserved",
            "Available",
            "Low stock limit",
            "Is low stock",
        ]
    ]
    item_rows.extend(
        [
            item["branch"],
            item["warehouse"],
            item["product"],
            item["sku"],
            item["category"],
            item["brand"],
            item["quantity"],
            item["reserved_quantity"],
            item["available_quantity"],
            item["low_stock_limit"],
            item["is_low_stock"],
        ]
        for item in report["items"]
    )
    return "inventory-report.xlsx", build_xlsx_workbook(
        {"Summary": summary_rows, "Inventory": item_rows}
    )


def debt_export():
    customer_rows = [["Customer", "Phone", "Extra phone", "Balance"]]
    customer_rows.extend(
        [row["full_name"], row["phone"], row["extra_phone"], row["balance"]]
        for row in customer_debts_report()
    )
    supplier_rows = [["Company", "Contact", "Phone", "Balance"]]
    supplier_rows.extend(
        [row["company_name"], row["full_name"], row["phone"], row["balance"]]
        for row in supplier_debts_report()
    )
    totals = total_debt_summary()
    summary_rows = [["Metric", "Value"]]
    summary_rows.extend([key, value] for key, value in totals.items())
    return "debt-report.xlsx", build_xlsx_workbook(
        {
            "Summary": summary_rows,
            "Customer debts": customer_rows,
            "Supplier debts": supplier_rows,
        }
    )
