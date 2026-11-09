# utility added by E. Schulze, updated for FT232R, CH340, and CP2102 interfaces
"""Utility to download e360 Cave Pearl data logger
Requires FT232R, CH340, or CP2102 USB to serial port adapter
Discovers serial port
sends download command
converts data to ISO8601 datetime (without decimal seconds)
allows timezone offset adjustments via CLI arguments
allows custom output file naming via CLI arguments
does some cleaning and re-naming
converts to .tsv
saves file
tested on MS-Windows
"""

import argparse
import time
from datetime import UTC, datetime, timedelta, timezone

import serial
import serial.tools.list_ports

# Configuration
BAUDRATE = 500000
TIMEOUT = 2  # Seconds to wait for new data before considering the stream ended
DEFAULT_OUTPUT_FILE = "cave_pearl_data.tsv"

# USB-to-Serial identifiers
FTDI_VID = 0x0403
CH340_VID = 0x1A86
CP2102_VID = 0x10C4  # Silicon Labs Vendor ID


def find_serial_port():
    """Automatically detects a connected FT232, CH340, or CP2102 USB-to-serial adapter.

    Scans available system COM ports for standard vendor identification
    or matching hardware description strings.

    Returns:
        str: The device path/port name if found, otherwise None.
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Check Vendor IDs or look for keywords in the description
        desc = (port.description or "").upper()
        is_ftdi = port.vid == FTDI_VID or "FT232" in desc
        is_ch340 = port.vid == CH340_VID or "CH340" in desc or "CH341" in desc
        is_cp2102 = port.vid == CP2102_VID or "CP210" in desc

        if is_ftdi or is_ch340 or is_cp2102:
            if is_ftdi:
                chip_type = "FTDI (FT232)"
            elif is_ch340:
                chip_type = "CH340"
            else:
                chip_type = "CP2102"

            print(f"[+] Logger detected on port: {port.device} ({port.description}) [{chip_type}]")
            return port.device
    return None


def convert_unix_to_iso(line, tz_offset=None, is_header=False):
    """Parses an incoming CSV line, extracts the Unix epoch timestamp from the first column,

    converts it into an ISO 8601 string adjusted by a UTC hour offset, and converts the separator to tabs (\t).
    Additionally removes any spaces from the column names if it is the header.

    Args:
        line (str): The raw comma-separated line from the logger.
        tz_offset (float/int, optional): The hour offset from UTC. If None, no tz suffix is added.
        is_header (bool): True if the line is the CSV header row.

    Returns:
        str: The reconstructed TSV line with the converted first column.
    """
    parts = line.split(",")

    if is_header:
        # Remove any leading/trailing spaces from each column name
        parts = [part.strip() for part in parts]
        # Rename the header column to Date_time
        parts[0] = "Date_time"
    else:
        try:
            # First extract base time in UTC
            unix_time = float(parts[0])
            dt_utc = datetime.fromtimestamp(unix_time, tz=UTC)
            dt_utc = dt_utc.replace(microsecond=0)

            if tz_offset is None:
                # Naive datetime: strip tz details completely
                dt_naive = dt_utc.replace(tzinfo=None)
                parts[0] = dt_naive.isoformat()
            elif tz_offset == 0:
                # Appended "Z" format for exact zero UTC offset
                dt_naive = dt_utc.replace(tzinfo=None)
                parts[0] = dt_naive.isoformat() + "Z"
            else:
                # Create a specific fixed timezone offset object
                target_tz = timezone(timedelta(hours=tz_offset))
                dt_adjusted = dt_utc.astimezone(target_tz)
                parts[0] = dt_adjusted.isoformat()

        except (ValueError, IndexError):
            # Fallback if the first column is corrupted or empty
            pass

    # Substitute commas with tabs for TSV output
    return "\t".join(parts)


def main():
    """Main execution loop to handle argument parsing, port discovery, automatic hardware reset,

    command transmission, stream filtering, and TSV formatting.




    """
    # Set up Command Line Argument Parsing
    parser = argparse.ArgumentParser(description="Download and convert e360 Cave Pearl data logger data.")
    parser.add_argument(
        "--offset",
        type=float,
        default=None,
        help="UTC hour offset designation (e.g., -5, 0, 3.5). Default is no timezone indication.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Path/name of the output TSV file. Default is '{DEFAULT_OUTPUT_FILE}'.",
    )
    args = parser.parse_args()

    port = find_serial_port()
    if not port:
        print("[-] No compatible FT232, CH340, or CP2102 USB-serial adapter found.")
        print("    Available ports were:")
        for p in serial.tools.list_ports.comports():
            print(f"    - {p.device}: {p.description} (VID: {p.vid}, PID: {p.pid})")
        return

    try:
        print(f"[...] Connecting to {port} at {BAUDRATE} baud...")
        # Opening the serial port triggers the automatic hardware DTR/RTS reset
        ser = serial.Serial(port, baudrate=BAUDRATE, timeout=TIMEOUT)

        # Flush buffers to ensure clean communication
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print("[+] Hardware auto-reset triggered successfully.")

        # Give the logger hardware a brief moment to reboot and stabilize
        time.sleep(1.5)

        print("[+] Sending download command ('1' + Enter)...")
        ser.write(b"1\n")
        ser.flush()

        print("[...] Collecting, filtering, and converting data stream to TSV...")
        print("[...] Stream will auto-close when no data is received for 2 seconds.")

        csv_started = False
        saved_lines_count = 0

        with open(args.output, "w", encoding="utf-8", newline="") as f:
            while True:
                line = ser.readline().decode("utf-8", errors="ignore")

                # If readline hits the timeout, it returns an empty string
                if not line:
                    break

                # Clean up whitespaces and newlines
                clean_line = line.strip()

                # Skip empty lines
                if not clean_line:
                    continue

                # Check for the start of the valid CSV Block (still incoming as CSV from logger)
                if not csv_started:
                    if clean_line.startswith("UnixTime"):
                        csv_started = True
                        # Process and write the updated header line
                        converted_line = convert_unix_to_iso(clean_line, tz_offset=args.offset, is_header=True)
                        f.write(converted_line + "\n")
                        f.flush()
                        saved_lines_count += 1
                        continue
                    else:
                        # Ignore boot information, menus, or pre-text
                        continue

                # Once data block started, identify the trailer by checking for the lack of a comma
                if csv_started and "," not in clean_line:
                    print("\n[+] End of data block detected (First non-CSV line encountered).")
                    break

                # Process data row (convert first column and switch separator to tab)
                converted_line = convert_unix_to_iso(clean_line, tz_offset=args.offset, is_header=False)

                # Write valid filtered line
                f.write(converted_line + "\n")
                f.flush()
                saved_lines_count += 1

                print(
                    f"\r-> {saved_lines_count} lines processed and saved...",
                    end="",
                    flush=True,
                )

        if csv_started and saved_lines_count > 1:
            print(f"\n\n[+] Success! Filtered data with 'Date_time' saved to '{args.output}'.")
        else:
            print("\n\n[-] Error: The 'UnixTime' marker was never found or data block was empty.")

    except serial.SerialException as e:
        print(f"\n[-] Serial error: {e}")
    except KeyboardInterrupt:
        print("\n[-] Operation cancelled by user.")
    finally:
        if "ser" in locals() and ser.is_open:
            ser.close()
            print("[+] Serial port closed.")


if __name__ == "__main__":
    main()
