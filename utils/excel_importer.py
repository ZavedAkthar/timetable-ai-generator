from openpyxl import load_workbook
from datetime import datetime, time, timedelta
import re


REQUIRED_SHEETS = {
    "Teachers": [
        "name", "email", "department", "designation",
        "max_hours_per_day", "max_hours_per_week", "status"
    ],
    "Classes": [
        "name", "department", "year", "section", "num_students"
    ],
    "Rooms": [
        "name", "building", "room_type", "capacity", "is_available"
    ],
    "Subjects": [
        "name", "code", "department", "class_name",
        "teacher_email", "hours_per_week", "subject_type"
    ],
    "Time Slots": [
        "period", "start_time", "end_time"
    ],
    "Teacher Availability": [
        "teacher_email", "day", "period", "is_available"
    ]
}

VALID_STATUSES = {"Available", "Absent", "Unavailable"}
VALID_ROOM_TYPES = {"Classroom", "Laboratory", "Seminar Hall"}
VALID_SUBJECT_TYPES = {"Theory", "Lab", "Tutorial"}
VALID_DAYS = {
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday"
}


def normalize_header(value):
    if value is None:
        return ""

    return str(value).strip().lower().replace(" ", "_")


def clean_value(value):
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining = seconds % 60
        return f"{hours:02}:{minutes:02}:{remaining:02}"

    if isinstance(value, (datetime, time)):
        return value.strftime("%H:%M:%S")

    if isinstance(value, str):
        return value.strip()

    return value


def normalize_email(value):
    return str(value).strip().lower()


def normalize_time(value):
    value = clean_value(value)

    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue

    raise ValueError(f"Invalid time value: {value}")


def normalize_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    if isinstance(value, str):
        value = value.strip().lower()

        if value in ("true", "yes", "1"):
            return True

        if value in ("false", "no", "0"):
            return False

    raise ValueError(f"Invalid boolean value: {value}")


def validate_positive(value, field):
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive number.")

    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a valid integer.")

    if number <= 0:
        raise ValueError(f"{field} must be greater than zero.")

    return number


def validate_email(value):
    email = normalize_email(value)

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.match(pattern, email):
        raise ValueError(f"Invalid email address: {value}")

    return email


def read_excel_file(file):
    data = {}
    errors = []

    try:
        workbook = load_workbook(
            file,
            read_only=True,
            data_only=True
        )
    except Exception as error:
        return {}, [f"Unable to read Excel file: {error}"]

    try:
        for sheet_name, required_columns in REQUIRED_SHEETS.items():

            if sheet_name not in workbook.sheetnames:
                errors.append(f"Missing worksheet: {sheet_name}")
                continue

            sheet = workbook[sheet_name]
            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, None)

            if not headers:
                errors.append(f"{sheet_name}: Worksheet is empty.")
                continue

            headers = [
                normalize_header(header)
                for header in headers
            ]

            if len(headers) != len(set(headers)):
                errors.append(
                    f"{sheet_name}: Duplicate column names found."
                )
                continue

            missing_columns = [
                column for column in required_columns
                if column not in headers
            ]

            if missing_columns:
                errors.append(
                    f"{sheet_name}: Missing columns: "
                    + ", ".join(missing_columns)
                )
                continue

            records = []

            for row_number, row in enumerate(rows, start=2):

                if not any(value is not None for value in row):
                    continue

                record = {}

                for index, column in enumerate(headers):
                    if column:
                        value = row[index] if index < len(row) else None
                        record[column] = clean_value(value)

                record["_row_number"] = row_number
                records.append(record)

            data[sheet_name] = records

    finally:
        workbook.close()

    if errors:
        return data, errors

    return data, validate_excel_data(data)


def validate_excel_data(data):
    errors = []

    def check_required(records, fields, sheet):
        for row in records:
            for field in fields:
                value = row.get(field)

                if value is None or str(value).strip() == "":
                    errors.append(
                        f"{sheet}, row {row['_row_number']}: "
                        f"{field} is required."
                    )

    def check_duplicates(records, field, sheet):
        seen = {}

        for row in records:
            value = row.get(field)

            if value is None:
                continue

            key = str(value).strip().lower()

            if key in seen:
                errors.append(
                    f"{sheet}, row {row['_row_number']}: "
                    f"Duplicate {field}: {value}."
                )
            else:
                seen[key] = row["_row_number"]

    teachers = data["Teachers"]
    classes = data["Classes"]
    rooms = data["Rooms"]
    subjects = data["Subjects"]
    slots = data["Time Slots"]
    availability = data["Teacher Availability"]

    # REQUIRED FIELDS

    for sheet, fields in REQUIRED_SHEETS.items():
        check_required(data[sheet], fields, sheet)

    # TEACHERS

    check_duplicates(teachers, "email", "Teachers")

    teacher_emails = set()

    for row in teachers:
        try:
            email = validate_email(row["email"])
            teacher_emails.add(email)

            max_day = validate_positive(
                row["max_hours_per_day"],
                "Maximum hours per day"
            )

            max_week = validate_positive(
                row["max_hours_per_week"],
                "Maximum hours per week"
            )

            if max_day > 24:
                raise ValueError("Maximum hours per day cannot exceed 24.")

            if max_week > 168:
                raise ValueError("Maximum hours per week cannot exceed 168.")

            if max_day > max_week:
                raise ValueError(
                    "Maximum daily hours cannot exceed weekly hours."
                )

            if row["status"] not in VALID_STATUSES:
                raise ValueError(
                    f"Invalid teacher status: {row['status']}"
                )

        except (ValueError, TypeError) as error:
            errors.append(
                f"Teachers, row {row['_row_number']}: {error}"
            )

    # CLASSES

    check_duplicates(classes, "name", "Classes")

    class_names = set()

    for row in classes:
        try:
            name = str(row["name"]).strip()
            class_names.add(name)

            year = validate_positive(row["year"], "Year")

            if year not in range(1, 5):
                raise ValueError("Year must be between 1 and 4.")

            validate_positive(row["num_students"], "Number of students")

        except (ValueError, TypeError) as error:
            errors.append(
                f"Classes, row {row['_row_number']}: {error}"
            )

    # ROOMS

    check_duplicates(rooms, "name", "Rooms")

    for row in rooms:
        try:
            validate_positive(row["capacity"], "Room capacity")

            if row["room_type"] not in VALID_ROOM_TYPES:
                raise ValueError(
                    f"Invalid room type: {row['room_type']}"
                )

            normalize_bool(row["is_available"])

        except (ValueError, TypeError) as error:
            errors.append(
                f"Rooms, row {row['_row_number']}: {error}"
            )

    # TIME SLOTS

    check_duplicates(slots, "period", "Time Slots")

    valid_periods = set()

    for row in slots:
        try:
            period = validate_positive(row["period"], "Period")

            start = normalize_time(row["start_time"])
            end = normalize_time(row["end_time"])

            if start >= end:
                raise ValueError("End time must be after start time.")

            valid_periods.add(period)

        except (ValueError, TypeError) as error:
            errors.append(
                f"Time Slots, row {row['_row_number']}: {error}"
            )

    # SUBJECTS

    subject_codes = set()

    for row in subjects:
        try:
            code = str(row["code"]).strip().lower()
            class_name = str(row["class_name"]).strip()
            email = validate_email(row["teacher_email"])

            unique_key = (code, class_name.lower())

            if unique_key in subject_codes:
                raise ValueError(
                    f"Duplicate subject code for class: {code}"
                )

            subject_codes.add(unique_key)

            if class_name not in class_names:
                raise ValueError(
                    f"Class not found in uploaded workbook: {class_name}"
                )

            if email not in teacher_emails:
                raise ValueError(
                    f"Teacher not found in uploaded workbook: {email}"
                )

            validate_positive(
                row["hours_per_week"],
                "Hours per week"
            )

            if row["subject_type"] not in VALID_SUBJECT_TYPES:
                raise ValueError(
                    f"Invalid subject type: {row['subject_type']}"
                )

        except (ValueError, TypeError) as error:
            errors.append(
                f"Subjects, row {row['_row_number']}: {error}"
            )

    # TEACHER AVAILABILITY

    availability_keys = set()

    for row in availability:
        try:
            email = validate_email(row["teacher_email"])

            if email not in teacher_emails:
                raise ValueError(
                    f"Teacher not found in uploaded workbook: {email}"
                )

            day = row["day"]

            if day not in VALID_DAYS:
                raise ValueError(f"Invalid day: {day}")

            period = validate_positive(row["period"], "Period")

            if period not in valid_periods:
                raise ValueError(
                    f"Period {period} not found in uploaded workbook."
                )

            normalize_bool(row["is_available"])

            key = (email, day, period)

            if key in availability_keys:
                raise ValueError(
                    "Duplicate teacher availability entry."
                )

            availability_keys.add(key)

        except (ValueError, TypeError) as error:
            errors.append(
                f"Teacher Availability, row {row['_row_number']}: {error}"
            )

    return errors