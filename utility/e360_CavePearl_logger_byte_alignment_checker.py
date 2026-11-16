import re
import sys
from pathlib import Path

VALID_RECORD_SIZES = {1, 2, 4, 8, 16}


def strip_comments(code: str) -> str:
    # Remove multi-line /* ... */ comments
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Remove single-line // comments
    lines = [line.split("//")[0] for line in code.splitlines()]
    return "\n".join(lines)


def get_active_defines(clean_code: str) -> set[str]:
    defines = set()
    for line in clean_code.splitlines():
        match = re.match(r"^\s*#define\s+([A-Za-z0-9_]+)", line)
        if match:
            defines.add(match.group(1))
    return defines


def find_sensor_byte_rules(clean_code: str) -> list[tuple[str, int]]:
    """
    Finds all #ifdef <MACRO> ... #endif blocks that add bytes to sensorBytesPerRecord.
    Supports:
      - sensorBytesPerRecord = sensorBytesPerRecord + 2;
      - sensorBytesPerRecord += 2;
      - sensorBytesPerRecord++;
    """
    rules = []
    # Match #ifdef <MACRO> blocks (non-nested)
    ifdef_pattern = re.compile(
        r"^\s*#ifdef\s+([A-Za-z0-9_]+)\s*\n(.*?)^\s*#endif",
        re.MULTILINE | re.DOTALL,
    )

    for match in ifdef_pattern.finditer(clean_code):
        macro = match.group(1)
        block = match.group(2)

        block_bytes = 0
        # Match: sensorBytesPerRecord = sensorBytesPerRecord + N
        for m in re.finditer(r"\bsensorBytesPerRecord\s*=\s*sensorBytesPerRecord\s*\+\s*(\d+)", block):
            block_bytes += int(m.group(1))

        # Match: sensorBytesPerRecord += N
        for m in re.finditer(r"\bsensorBytesPerRecord\s*\+=\s*(\d+)", block):
            block_bytes += int(m.group(1))

        # Match: sensorBytesPerRecord++ or ++sensorBytesPerRecord
        for _ in re.finditer(r"(\bsensorBytesPerRecord\s*\+\+|\+\+\s*sensorBytesPerRecord\b)", block):
            block_bytes += 1

        if block_bytes > 0:
            rules.append((macro, block_bytes))

    return rules


def check_ino(filepath: str) -> bool:
    path = Path(filepath)
    if not path.is_file():
        print(f"Error: File '{filepath}' not found.")
        return False

    raw_code = path.read_text(encoding="utf-8", errors="ignore")
    clean_code = strip_comments(raw_code)

    active_defines = get_active_defines(clean_code)
    sensor_rules = find_sensor_byte_rules(clean_code)

    total_bytes = 0

    print(f"File: {path.name}")
    print("=" * 50)
    print("Detected Sensor Byte Rules in Code:")

    if not sensor_rules:
        print("  (No 'sensorBytesPerRecord' #ifdef blocks found!)")
    else:
        for macro, size in sensor_rules:
            is_active = macro in active_defines
            status = "ACTIVE" if is_active else "off"
            if is_active:
                total_bytes += size
                print(f"  [+{size}B] {macro:<25} ({status})")
            else:
                print(f"  [  0B] {macro:<25} ({status})")

    print("=" * 50)
    print(f"Total Active Data Frame Size: {total_bytes} byte(s)")

    if total_bytes in VALID_RECORD_SIZES:
        print("STATUS: PASS (Valid 1, 2, 4, 8, or 16 bytes)")
        return True
    else:
        print("STATUS: FAIL (Must equal 1, 2, 4, 8, or 16 bytes!)")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_e360_bytes.py <your_file.ino>")
        sys.exit(1)

    ok = check_ino(sys.argv[1])
    sys.exit(0 if ok else 1)
