#!/usr/bin/env python3
"""Patch tick-stock-panel so it can run behind YSJ at /tick-panel.

The script is intentionally idempotent and keeps one backup beside every
modified source file. Run it on the EC2 checkout before rebuilding Docker.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


APP_BASE_SOURCE = """const PROXY_BASE = '/tick-panel'

export const APP_BASE = (
  window.location.pathname === PROXY_BASE
  || window.location.pathname.startsWith(`${PROXY_BASE}/`)
) ? PROXY_BASE : ''

export function withAppBase(value: string): string {
  if (!APP_BASE || !value.startsWith('/api/')) return value
  return `${APP_BASE}${value}`
}

let transportInstalled = false

export function installAppBaseTransport(): void {
  if (!APP_BASE || transportInstalled) return
  transportInstalled = true

  const nativeFetch = window.fetch.bind(window)
  window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    if (typeof input === 'string') {
      return nativeFetch(withAppBase(input), init)
    }
    if (input instanceof URL && input.origin === window.location.origin) {
      const path = withAppBase(`${input.pathname}${input.search}${input.hash}`)
      return nativeFetch(new URL(path, input.origin), init)
    }
    return nativeFetch(input, init)
  }) as typeof window.fetch

  const NativeEventSource = window.EventSource
  class AppBaseEventSource extends NativeEventSource {
    constructor(url: string | URL, eventSourceInitDict?: EventSourceInit) {
      const nextUrl = typeof url === 'string' ? withAppBase(url) : url
      super(nextUrl, eventSourceInitDict)
    }
  }
  window.EventSource = AppBaseEventSource as typeof EventSource
}
"""


def replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise RuntimeError(f"Expected source text not found in {path}")
    backup = path.with_suffix(path.suffix + ".pre-ysj-base-path")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").expanduser().resolve()
    frontend = root / "frontend" / "src"
    required = [frontend / "main.tsx", frontend / "router.tsx", frontend / "lib" / "api.ts"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("Not a tick-stock-panel checkout; missing:", *missing, sep="\n  ", file=sys.stderr)
        return 2

    app_base = frontend / "lib" / "appBase.ts"
    if not app_base.exists():
        app_base.write_text(APP_BASE_SOURCE, encoding="utf-8")

    changed = []
    main_path = frontend / "main.tsx"
    if replace_once(
        main_path,
        "import './index.css'\n",
        "import './index.css'\nimport { APP_BASE, installAppBaseTransport } from './lib/appBase'\n\ninstallAppBaseTransport()\n",
    ):
        changed.append(main_path)
    if replace_once(
        main_path,
        "    if (window.location.pathname === '/login') return\n",
        "    if (window.location.pathname === `${APP_BASE}/login`) return\n",
    ):
        changed.append(main_path)
    if replace_once(
        main_path,
        "    const redirect = encodeURIComponent(window.location.pathname + window.location.search)\n"
        "    window.location.href = `/login?redirect=${redirect}`\n",
        "    const routePath = window.location.pathname.slice(APP_BASE.length) || '/'\n"
        "    const redirect = encodeURIComponent(routePath + window.location.search)\n"
        "    window.location.href = `${APP_BASE}/login?redirect=${redirect}`\n",
    ):
        changed.append(main_path)

    router_path = frontend / "router.tsx"
    if replace_once(
        router_path,
        "import { createBrowserRouter, Navigate } from 'react-router-dom'\n",
        "import { createBrowserRouter, Navigate } from 'react-router-dom'\n"
        "import { APP_BASE } from './lib/appBase'\n",
    ):
        changed.append(router_path)
    router_text = router_path.read_text(encoding="utf-8")
    if "], { basename: APP_BASE || '/' })" not in router_text:
        marker = "\n])\n"
        if not router_text.endswith(marker):
            raise RuntimeError(f"Unexpected router ending in {router_path}")
        backup = router_path.with_suffix(router_path.suffix + ".pre-ysj-base-path")
        if not backup.exists():
            shutil.copy2(router_path, backup)
        router_path.write_text(
            router_text[: -len(marker)] + "\n], { basename: APP_BASE || '/' })\n",
            encoding="utf-8",
        )
        changed.append(router_path)

    api_path = frontend / "lib" / "api.ts"
    if replace_once(
        api_path,
        "import { toast } from '@/components/Toast'\n\nconst BASE = ''\n",
        "import { toast } from '@/components/Toast'\n"
        "import { APP_BASE } from './appBase'\n\n"
        "const BASE = APP_BASE\n",
    ):
        changed.append(api_path)

    print("YSJ base-path patch is ready.")
    for path in dict.fromkeys(changed):
        print(f"  updated: {path.relative_to(root)}")
    if not changed:
        print("  no changes needed; patch was already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
