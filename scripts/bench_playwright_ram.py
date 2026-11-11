#!/usr/bin/env python3
"""Playwright RAM rehearsal: NOT an Adam/Wayland acceptance test.

Creates isolated Chromium profile, two controlled tabs and blocks image/media/font
requests. Saves samples for MemAvailable and Chromium process proportional set size.
No SLM, ElevenLabs, desktop control, or privileged OS integration is present.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time


FIXTURE = b"""<!doctype html><html><head><title>Adam RAM fixture</title></head>
<body><h1>Adam RAM Test</h1><img src="/picture.jpg" alt="test">
<video src="/clip.mp4" preload="auto" muted autoplay></video>
<script>
for (let i=0;i<350;i++){let x=document.createElement('p');x.textContent='item '+i;
document.body.appendChild(x);}
</script></body></html>"""


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
    """Chromium *profile process tree* PSS; may be unavailable on some kernels."""
    table = {}
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            cmdline = (Path(entry.path)/"cmdline").read_bytes().replace(b"\0",b" ").decode("utf-8","replace")
            status = (Path(entry.path)/"status").read_text(encoding="utf-8")
            parent = next(int(x.split()[1]) for x in status.splitlines() if x.startswith("PPid:"))
        except (OSError, StopIteration, ValueError):
            continue
        table[pid] = (parent, cmdline)

    roots = {pid for pid,(_,cmd) in table.items() if "--user-data-dir="+profile_dir in cmd}
    children = set(roots)
    while True:
        expanded = children | {pid for pid,(parent,_) in table.items() if parent in children}
        if expanded == children:
            break
        children = expanded

    total_pss_kib = 0
    observed = 0
    for pid in children:
        try:
            for line in Path("/proc",str(pid),"smaps_rollup").read_text(encoding="utf-8").splitlines():
                if line.startswith("Pss:"):
                    total_pss_kib += int(line.split()[1])
                    observed += 1
                    break
        except (OSError, ValueError, IndexError):
            continue
    return {"browser_processes":len(children),"pss_measured_processes":observed,
            "browser_pss_mib":round(total_pss_kib/1024,1) if observed else None}


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/","/index.html"):
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(FIXTURE)
        elif self.path in ("/picture.jpg","/clip.mp4"):
            self.send_response(200)
            self.send_header("Content-Type","image/jpeg" if self.path.endswith(".jpg") else "video/mp4")
            self.end_headers()
            self.wfile.write(b"fake-media-payload")
        else:
            self.send_error(404)

    def log_message(self,*args):
        pass


async def run(args):
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Install: python -m pip install playwright && python -m playwright install chromium") from exc

    out = Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    blocked = Counter()
    server = ThreadingHTTPServer(("127.0.0.1",0),FixtureHandler)
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    fixture_url = "http://127.0.0.1:%d/" % server.server_port
    samples = []
    denied_third_tab = False
    started = time.monotonic()

    try:
        with tempfile.TemporaryDirectory(prefix="adam-browser-profile-") as profile:
            async with async_playwright() as playwright:
                context = await playwright.chromium.launch_persistent_context(
                    profile, headless=not args.headed, service_workers="block",
                    args=["--disable-background-networking","--disable-sync","--no-first-run"],
                    viewport={"width":1100,"height":700})
                try:
                    for page in list(context.pages):
                        await page.close()

                    async def handler(route):
                        kind = route.request.resource_type
                        if kind in ("image","media","font"):
                            blocked[kind] += 1
                            await route.abort()
                        else:
                            await route.continue_()

                    await context.route("**/*",handler)

                    def on_page(page):
                        if len([p for p in context.pages if not p.is_closed()]) > 2:
                            asyncio.create_task(page.close())
                    context.on("page",on_page)

                    async def controlled_page():
                        if len([p for p in context.pages if not p.is_closed()]) >= 2:
                            raise RuntimeError("tab_cap_reached")
                        return await context.new_page()

                    pages=[]
                    for i in range(2):
                        page = await controlled_page()
                        pages.append(page)
                        await page.goto(fixture_url,wait_until="load",timeout=15000)

                    try:
                        await controlled_page()
                    except RuntimeError as error:
                        denied_third_tab = str(error)=="tab_cap_reached"

                    if args.url:
                        await pages[0].goto(args.url,wait_until="domcontentloaded",timeout=20000)

                    # Append samples to disk during test to preserve evidence on interruption.
                    with out.open("w",encoding="utf-8") as stream:
                        while time.monotonic()-started < args.seconds:
                            snap=process_snapshot(profile)
                            snap.update({
                                "elapsed_s":round(time.monotonic()-started,2),
                                "mem_available_mib":mem_available_mib(),
                                "open_tabs":len([p for p in context.pages if not p.is_closed()]),
                                "blocked":dict(blocked)})
                            samples.append(snap)
                            stream.write(json.dumps(snap,ensure_ascii=False)+"\n")
                            stream.flush()
                            await asyncio.sleep(.5)
                finally:
                    await context.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    known_pss=[x["browser_pss_mib"] for x in samples if x["browser_pss_mib"] is not None]
    known_mem=[x["mem_available_mib"] for x in samples if x["mem_available_mib"] is not None]
    peak_pss=max(known_pss) if known_pss else None
    min_mem=min(known_mem) if known_mem else None
    max_tabs=max((x["open_tabs"] for x in samples),default=0)
    if not known_pss or not known_mem or not samples:
        result="inconclusive"
    elif peak_pss>1280 or min_mem<1536 or max_tabs>2 or not denied_third_tab or blocked["image"]<2:
        result="fail"
    else:
        result="pass"
    summary={"result":result,"sample_count":len(samples),
             "peak_browser_pss_mib":peak_pss,"min_mem_available_mib":min_mem,
             "maximum_observed_tabs":max_tabs,"third_tab_denied":denied_third_tab,
             "blocked":dict(blocked),"profile_isolated":True,
             "tts_tested":False,"slm_tested":False,"stt_tested":False,
             "wayland_tested":False,"homologation_completed":False,
             "data_file":str(out)}
    summary_path=out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if result=="pass" else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds",type=int,default=120)
    parser.add_argument("--headed",action="store_true",help="Abrir janela visível no desktop real")
    parser.add_argument("--url",help="URL pública de teste a carregar na primeira aba após teste da fixture")
    parser.add_argument("--out",default="artifacts/week1/browser_ram.jsonl")
    args=parser.parse_args()
    if not 5<=args.seconds<=900:
        parser.error("--seconds must be between 5 and 900")
    return asyncio.run(run(args))


if __name__=="__main__":
    raise SystemExit(main())
