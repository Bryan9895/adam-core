#!/usr/bin/env python3
"""Stress de ciclos Playwright/Chromium, SEM homologacao do Adam ou Wayland.

O modo de gate exige >= 1800 s e coleta amostras durante abertura, navegacao,
extracao, fechamento e ociosidade. O smoke curto serve apenas para depuracao.
Nao usa credenciais nem websites privados. Requer Linux /proc e Playwright.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import statistics
import tempfile
import threading
import time

MIN_GATE_SECONDS = 1800
MAX_TABS = 2
MAX_BROWSER_PSS_MIB = 1280
MIN_MEM_AVAILABLE_MIB = 1536
MAX_POST_CLOSE_GROWTH_MIB = 128


def mem_available_mib(source="/proc/meminfo"):
    try:
        content = Path(source).read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("MemAvailable:"):
                return round(int(line.split()[1]) / 1024, 1)
    except (OSError, ValueError, IndexError):
        pass
    return None


def process_snapshot(profile_dir):
    """Somatorio PSS/RSS dos processos Chromium pertencentes ao perfil isolado."""
    table = {}
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            cmdline = (Path(entry.path)/"cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
            status = (Path(entry.path)/"status").read_text(encoding="utf-8")
            parent = next(int(x.split()[1]) for x in status.splitlines() if x.startswith("PPid:"))
        except (OSError, StopIteration, ValueError):
            continue
        table[pid] = (parent, cmdline)
    roots = {pid for pid, (_,cmd) in table.items() if "--user-data-dir=" + profile_dir in cmd}
    children = set(roots)
    while True:
        expanded = children | {pid for pid,(parent,_) in table.items() if parent in children}
        if expanded == children:
            break
        children = expanded

    pss_kib = 0
    rss_kib = 0
    count_pss = 0
    for pid in children:
        try:
            lines = Path("/proc", str(pid), "smaps_rollup").read_text(encoding="utf-8").splitlines()
            pss_kib += int(next(x.split()[1] for x in lines if x.startswith("Pss:")))
            rss_kib += int(next(x.split()[1] for x in lines if x.startswith("Rss:")))
            count_pss += 1
        except (OSError, ValueError, IndexError, StopIteration):
            continue
    return {
        "browser_processes": len(children),
        "pss_measured_processes": count_pss,
        "browser_pss_mib": round(pss_kib/1024, 2) if count_pss else None,
        "browser_rss_sum_mib": round(rss_kib/1024, 2) if count_pss else None
    }


# A fixture local usa DOM progressivamente complexo e recursos descartaveis.
def page_html(path):
    variant = 600 if path.startswith("/heavy") else 200
    return ("""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Adam stress fixture</title>
<style>.item{margin:2px;padding:2px;border:1px solid #ddd}</style></head><body>
<h1 id="ready">Adam browser RAM test</h1><img src="/picture.jpg">
<video src="/clip.mp4" preload="auto" muted autoplay></video>
<section id="content"></section>
<script>
const root=document.querySelector('#content');
for(let i=0;i<""" + str(variant) + """;i++){
  const el=document.createElement("article");
  el.className="item";
  el.dataset.index=i;
  el.textContent="Ciclo de DOM — conteúdo sintético "+i;
  root.appendChild(el);
}
window.TEST_READY=true;
</script></body></html>""").encode("utf-8")


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith(("/heavy", "/light")) or self.path == "/":
            body = page_html(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif self.path in ("/picture.jpg", "/clip.mp4"):
            body = b"fixture-not-real-media"
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg" if self.path.endswith(".jpg") else "video/mp4")
        else:
            self.send_error(404)
            return
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def evaluate(samples, events, seconds, blocked, third_denied, errors):
    metric = [x for x in samples if x["kind"] == "metric"]
    pss = [x["browser_pss_mib"] for x in metric if x["browser_pss_mib"] is not None]
    avail = [x["mem_available_mib"] for x in metric if x["mem_available_mib"] is not None]
    close_pss = [x["browser_pss_mib"] for x in metric if x["phase"] == "post_close" and x["browser_pss_mib"] is not None]
    initial = statistics.median(close_pss[:5]) if len(close_pss) >= 10 else None
    final = statistics.median(close_pss[-5:]) if len(close_pss) >= 10 else None
    growth = round(final - initial, 2) if initial is not None else None
    max_tabs = max((x["open_tabs"] for x in metric), default=0)
    cycles = sum(x["event"] == "cycle_completed" for x in events)
    ended = any(x["event"] == "test_finished" for x in events)
    duration = max((x["elapsed_s"] for x in events), default=0)
    min_samples = max(30, int(seconds / 2 * 0.70))  # tolerancia para IO lento
    inconclusive = (
        seconds < MIN_GATE_SECONDS or not ended or cycles < 10 or
        len(metric) < min_samples or len(pss) < len(metric) * .95 or
        len(avail) < len(metric) * .95 or growth is None
    )
    violated = (
        errors or (pss and max(pss) > MAX_BROWSER_PSS_MIB) or
        (avail and min(avail) < MIN_MEM_AVAILABLE_MIB) or
        max_tabs > MAX_TABS or growth is not None and growth > MAX_POST_CLOSE_GROWTH_MIB or
        blocked["image"] < cycles or not third_denied
    )
    status = "fail" if violated else ("inconclusive" if inconclusive else "pass")
    return {
        "result": status,
        "requested_s": seconds,
        "observed_duration_s": round(duration, 2),
        "completed_cycles": cycles,
        "sample_count": len(metric),
        "maximum_observed_tabs": max_tabs,
        "third_tab_denied": third_denied,
        "blocked": dict(blocked),
        "peak_browser_pss_mib": max(pss) if pss else None,
        "peak_browser_rss_sum_mib": max(
            (x["browser_rss_sum_mib"] for x in metric if x["browser_rss_sum_mib"] is not None),
            default=None
        ),
        "min_mem_available_mib": min(avail) if avail else None,
        "post_close_pss_growth_mib": growth,
        "failure_events": errors,
        "gate_thresholds": {
            "duration_s": MIN_GATE_SECONDS, "pss_mib": MAX_BROWSER_PSS_MIB,
            "mem_available_mib": MIN_MEM_AVAILABLE_MIB,
            "max_tabs": MAX_TABS,
            "post_close_growth_mib": MAX_POST_CLOSE_GROWTH_MIB
        },
        "wayland_tested": False,
        "homologation_completed": False,
        "slm_tested": False,
        "stt_tested": False,
        "tts_tested": False
    }


async def run(args):
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Instale playwright e Chromium: python -m pip install playwright && python -m playwright install chromium") from exc

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % server.server_port
    samples, events, blocked, errors = [], [], Counter(), []
    phase = "boot"
    cycle = 0
    third_denied = False
    stop = asyncio.Event()
    try:
        # O JSONL fica aberto/flushado para preservar a ultima amostra apos OOM/SIGKILL.
        with out.open("w", encoding="utf-8", buffering=1) as stream:
            def record(row):
                row = dict(row, elapsed_s=round(time.monotonic()-started, 3))
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                if row["kind"] == "metric":
                    samples.append(row)
                else:
                    events.append(row)

            with tempfile.TemporaryDirectory(prefix="adam-browser-profile-") as profile:
                async with async_playwright() as p:
                    context = await p.chromium.launch_persistent_context(
                        profile,
                        headless=not args.headed,
                        service_workers="block",
                        viewport={"width": 1100, "height": 700},
                        args=["--disable-background-networking", "--disable-sync", "--no-first-run"],
                        **({"executable_path": args.chromium_exe} if args.chromium_exe else {})
                    )
                    try:
                        async def route_handler(route):
                            kind = route.request.resource_type
                            if kind in ("image", "media", "font"):
                                blocked[kind] += 1
                                await route.abort()
                            else:
                                await route.continue_()
                        await context.route("**/*", route_handler)

                        async def cap_excess(page):
                            if len([x for x in context.pages if not x.is_closed()]) > MAX_TABS:
                                errors.append("unexpected_tab_created")
                                await page.close()

                        def page_event(page):
                            asyncio.create_task(cap_excess(page))
                        context.on("page", page_event)

                        # Fecha abas iniciais que possam ter sido criadas pelo navegador.
                        for page in list(context.pages):
                            await page.close()

                        async def new_tab():
                            if len([x for x in context.pages if not x.is_closed()]) >= MAX_TABS:
                                raise RuntimeError("tab_cap_reached")
                            return await context.new_page()

                        async def sample_loop():
                            while not stop.is_set():
                                snapshot = process_snapshot(profile)
                                record({
                                    "kind": "metric", "cycle": cycle, "phase": phase,
                                    "open_tabs": len([x for x in context.pages if not x.is_closed()]),
                                    "mem_available_mib": mem_available_mib(),
                                    **snapshot
                                })
                                await asyncio.sleep(0.5)

                        sampler = asyncio.create_task(sample_loop())
                        try:
                            first = await new_tab()
                            second = await new_tab()
                            try:
                                await new_tab()
                            except RuntimeError as exc:
                                third_denied = str(exc) == "tab_cap_reached"
                            await second.close()
                            await first.close()

                            # Ciclo de vida: criar → navegar → DOM → extrair → fechar → ocioso.
                            while time.monotonic() - started < args.seconds:
                                cycle += 1
                                phase = "open"
                                tab = await new_tab()
                                try:
                                    phase = "navigate"
                                    await tab.goto(base + ("/heavy" if cycle % 2 else "/light"),
                                                   wait_until="domcontentloaded", timeout=20000)
                                    await tab.wait_for_function("window.TEST_READY === true", timeout=8000)
                                    phase = "extract"
                                    count = await tab.locator("#content article").count()
                                    if count < 200:
                                        raise RuntimeError("dom_incomplete")
                                    # Simula parse do DOM e script temporario sem dados pessoais.
                                    await tab.evaluate("""() => {
                                        const x = document.createElement('div');
                                        x.textContent = [...document.querySelectorAll('article')]
                                            .slice(0, 20).map(e => e.textContent).join('|');
                                        document.body.appendChild(x);
                                        x.remove();
                                    }""")
                                    record({"kind": "event", "event": "data_extracted",
                                            "cycle": cycle, "dom_elements": count})
                                finally:
                                    phase = "close"
                                    await tab.close()
                                phase = "post_close"
                                record({"kind": "event", "event": "cycle_completed", "cycle": cycle})
                                await asyncio.sleep(args.idle_s)
                        except Exception as exc:
                            errors.append(type(exc).__name__ + ": " + str(exc)[:120])
                            record({"kind": "event", "event": "test_failed", "cycle": cycle,
                                    "error": errors[-1]})
                        finally:
                            stop.set()
                            await sampler
                            record({"kind": "event", "event": "test_finished", "cycle": cycle})
                    finally:
                        await context.close()
    finally:
        server.shutdown()
        server.server_close()

    summary = evaluate(samples, events, args.seconds, blocked, third_denied, errors)
    summary["data_file"] = str(out)
    out.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["result"] == "pass" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=1800)
    parser.add_argument("--idle-s", type=float, default=1.5)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--chromium-exe", help="Chromium do sistema (opcional)")
    parser.add_argument("--out", default="artifacts/week1/browser_ram.jsonl")
    args = parser.parse_args()
    if not 10 <= args.seconds <= 7200:
        parser.error("--seconds deve estar entre 10 e 7200")
    if not 0.1 <= args.idle_s <= 30:
        parser.error("--idle-s deve estar entre 0.1 e 30")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
