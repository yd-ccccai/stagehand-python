from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from stagehand.a11y.utils import get_accessibility_tree
from .security import validate_tool_args


async def tool_dispatch(stagehand, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a tool call by name to its executor.
    """
    args = validate_tool_args(name, args or {})
    if name == "goto":
        return await tool_goto(stagehand, args)
    if name == "navback":
        return await tool_navback(stagehand, args)
    if name == "act":
        return await tool_act(stagehand, args)
    if name == "fillForm":
        return await tool_fill_form(stagehand, args)
    if name == "extract":
        return await tool_extract(stagehand, args)
    if name == "ariaTree":
        return await tool_aria_tree(stagehand)
    if name == "screenshot":
        return await tool_screenshot(stagehand)
    if name == "scroll":
        return await tool_scroll(stagehand, args)
    if name == "wait":
        return await tool_wait(stagehand, args)
    if name == "close":
        return await tool_close(args)
    return {"success": False, "error": f"Unknown tool: {name}"}


async def tool_goto(stagehand, args: Dict[str, Any]) -> Dict[str, Any]:
    url = args.get("url")
    if not url or not url.lower().startswith(("http://", "https://")):
        return {"success": False, "error": "Invalid URL: must start with http(s)"}
    await stagehand.page.goto(url)
    return {"success": True, "url": url}


async def tool_navback(stagehand, args: Dict[str, Any]) -> Dict[str, Any]:
    await stagehand.page.go_back()
    return {"success": True, "url": stagehand.page._page.url}


async def tool_act(stagehand, args: Dict[str, Any]) -> Dict[str, Any]:
    action = args.get("action")
    variables = args.get("variables")
    result = await stagehand.page.act(action, variables=variables)
    # Normalize to dict
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    return {"success": bool(result.get("success", True)), "detail": result}


async def tool_fill_form(stagehand, args: Dict[str, Any]) -> Dict[str, Any]:
    fields: List[Dict[str, Any]] = args.get("fields", [])
    per_field: List[Tuple[str, Any]] = []
    all_ok = True
    for field in fields:
        action = field.get("action")
        value = field.get("value")
        res = await stagehand.page.act(action, variables={"value": value})
        if hasattr(res, "model_dump"):
            res = res.model_dump()
        ok = bool(res.get("success", True))
        all_ok = all_ok and ok
        per_field.append((action, ok))
    return {"success": all_ok, "fields": per_field}


async def tool_extract(stagehand, args: Dict[str, Any]) -> Dict[str, Any]:
    instruction = args.get("instruction")
    schema = args.get("schema")
    result = await stagehand.page.extract(instruction, schema=schema)
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    return {"success": True, "data": result}


async def tool_aria_tree(stagehand) -> Dict[str, Any]:
    tree = await get_accessibility_tree(stagehand.page, stagehand.logger)
    simplified = tree.get("simplified", "")
    # Avoid hard caps; still trim excessive whitespace
    return {"success": True, "tree": simplified}


async def tool_screenshot(stagehand) -> Dict[str, Any]:
    png_bytes = await stagehand.page._page.screenshot(full_page=False, type="png")
    b64 = base64.b64encode(png_bytes).decode()
    return {
        "success": True,
        "image": {"type": "image", "mimeType": "image/png", "data": b64},
        "url": stagehand.page._page.url,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


async def tool_scroll(stagehand, args: Dict[str, Any]) -> Dict[str, Any]:
    pixels = int(args.get("pixels", 0))
    direction = args.get("direction", "down")
    dy = pixels if direction == "down" else -pixels
    await stagehand.page._page.mouse.wheel(0, dy)
    return {"success": True, "scrolled": dy}


async def tool_wait(stagehand, args: Dict[str, Any]) -> Dict[str, Any]:
    time_ms = int(args.get("timeMs", 0))
    await stagehand.page._page.wait_for_timeout(time_ms)
    return {"success": True, "waitedMs": time_ms}


async def tool_close(args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": bool(args.get("success", False)),
        "completed": True,
        "message": args.get("reasoning"),
    }
