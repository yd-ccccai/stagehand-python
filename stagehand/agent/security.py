from __future__ import annotations

from typing import Any, Dict


def sanitize_url(url: str) -> str:
    """
    Basic URL sanitation: strip whitespace; allow http(s) only.
    """
    url = (url or "").strip()
    if not url:
        return url
    lowered = url.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        return url  # Allow caller to validate/raise; do not auto-rewrite
    return url


def clamp_scroll_pixels(pixels: int) -> int:
    """Prevent extreme scrolling jumps while avoiding hard-coded model limits."""
    if pixels < 0:
        pixels = -pixels
    # Cap to a reasonable per-step delta; callers decide step count
    return min(pixels, 4000)


def validate_tool_args(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight validation/normalization for tool args.
    """
    if name == "goto" and isinstance(args.get("url"), str):
        args["url"] = sanitize_url(args["url"])
    if name == "scroll":
        try:
            p = int(args.get("pixels", 0))
        except Exception:
            p = 0
        args["pixels"] = clamp_scroll_pixels(p)
        if args.get("direction") not in ("up", "down"):
            args["direction"] = "down"
    if name == "wait":
        try:
            t = int(args.get("timeMs", 0))
        except Exception:
            t = 0
        args["timeMs"] = max(0, t)
    return args


__all__ = [
    "sanitize_url",
    "clamp_scroll_pixels",
    "validate_tool_args",
]
