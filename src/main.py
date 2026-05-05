import importlib
import platform
import subprocess
import sys
from pathlib import Path


OUTPUT_PATH = Path("/app/outputs/env_check.txt")


def check_import(module_name, display_name):
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "version unknown")
        return True, f"[OK] {display_name} import: {version}"
    except Exception as exc:
        return False, f"[FAIL] {display_name} import: {type(exc).__name__}: {exc}"


def check_command(command, display_name):
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or result.stderr).strip()
        first_line = output.splitlines()[0] if output else "no version output"
        return True, f"[OK] {display_name}: {first_line}"
    except FileNotFoundError as exc:
        return False, f"[FAIL] {display_name}: command not found: {exc}"
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        return False, f"[FAIL] {display_name}: {details}"
    except Exception as exc:
        return False, f"[FAIL] {display_name}: {type(exc).__name__}: {exc}"


def main():
    checks = []
    checks.append((True, f"[OK] Python: {platform.python_version()} ({sys.executable})"))
    checks.append(check_import("cv2", "OpenCV (cv2)"))
    checks.append(check_import("numpy", "NumPy"))
    checks.append(check_import("PIL", "Pillow (PIL)"))
    checks.append(check_command(["fontforge", "--version"], "FontForge"))
    checks.append(check_command(["potrace", "--version"], "Potrace"))

    lines = [
        "handwrite2350 Docker environment check",
        "=" * 40,
        *[message for _, message in checks],
    ]

    failed = [message for ok, message in checks if not ok]
    lines.extend(
        [
            "",
            f"Result: {'FAIL' if failed else 'PASS'}",
            f"Failed checks: {len(failed)}",
        ]
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_text = "\n".join(lines) + "\n"
    OUTPUT_PATH.write_text(output_text, encoding="utf-8")
    print(output_text, end="")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
