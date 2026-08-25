import re


class FileSizeHelper:
    @classmethod
    def convert_size_to_bytes(cls, size: str) -> int | None:
        parsed = cls._parse_size_string(size)
        if not parsed:
            return None

        number, unit = parsed
        unit_multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4, "PB": 1024**5}

        if unit not in unit_multipliers:
            return None

        return int(number * unit_multipliers[unit])

    @classmethod
    def bytes_to_human_readable(cls, bytes_value: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB", "PB"]

        for unit in reversed(units):
            divisor = 1 if unit == "B" else 1024 ** units.index(unit)

            if bytes_value >= divisor:
                value = bytes_value / divisor
                if value == int(value):
                    return f"{int(value)}{unit}"
                return f"{value:.1f}{unit}"

        return f"{bytes_value}B"

    @classmethod
    def _is_size_format(cls, text: str) -> bool:
        pattern = r"^\d+(?:\.\d+)?(?:B|KB|MB|GB|TB|PB)$"
        return bool(re.match(pattern, text.strip(), re.IGNORECASE))

    @classmethod
    def _parse_size_string(cls, text: str) -> tuple[float, str] | None:
        if not cls._is_size_format(text):
            return None

        pattern = r"^(\d+(?:\.\d+)?)(.*?)$"
        match = re.match(pattern, text.strip(), re.IGNORECASE)

        if match:
            number = float(match.group(1))
            unit = match.group(2).upper()
            return number, unit

        return None
