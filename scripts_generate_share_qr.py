from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

import qrcode


def _valid_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must include http(s) scheme and host, e.g. https://mybot.onrender.com")
    return value.rstrip("/")


def build_qr(url: str, output_path: Path) -> Path:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a PNG QR code for a deployed HappyBot URL.")
    parser.add_argument("--url", required=True, type=_valid_url, help="Public HTTPS URL of deployed app")
    parser.add_argument("--out", default="happybot_qr.png", help="Output PNG path (default: happybot_qr.png)")
    args = parser.parse_args()

    output = build_qr(args.url, Path(args.out))
    print(f"QR generated: {output.resolve()}")
    print(f"Scans open: {args.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
