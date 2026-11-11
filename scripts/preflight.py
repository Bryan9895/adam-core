#!/usr/bin/env python3
"""Diagnóstico passivo. Não é homologação do Alpha e não age no desktop."""
from __future__ import annotations
import argparse
import json
import os
import platform
import shutil
from pathlib import Path

def meminfo_gib(source="/proc/meminfo"):
    try:
        raw=Path(source).read_text(encoding="utf-8")
    except OSError:
        return {}
    values={}
    for line in raw.splitlines():
        name,sep,rest=line.partition(":")
        if sep and name in ("MemTotal","MemAvailable","SwapTotal","SwapFree"):
            parts=rest.strip().split()
            if len(parts)>1 and parts[1]=="kB":
                try:
                    values[name+"_gib"]=round(int(parts[0])/1024/1024,3)
                except ValueError:
                    pass
    return values

def check_environment(env=None):
    cfg=dict(os.environ) if env is None else env
    session=cfg.get("XDG_SESSION_TYPE","unknown").lower()
    desktop=cfg.get("XDG_CURRENT_DESKTOP","unknown")
    result={
        "purpose":"preflight_only_not_an_alpha_acceptance_test",
        "platform":platform.platform(),
        "python_version":platform.python_version(),
        "session_type":session,
        "desktop":desktop,
        "wayland_session":session=="wayland",
        "gnome_session":"GNOME" in desktop.upper(),
        "programs_available":{p:shutil.which(p) is not None for p in ("python3","gdbus","busctl","firefox","code","node","npm")},
        "memory":meminfo_gib(),
        "tts_provider":cfg.get("ADAM_TTS_PROVIDER","elevenlabs"),
        "tts_local_enabled":cfg.get("ADAM_TTS_LOCAL_ENABLED","false").lower()=="true",
        "elevenlabs_key_configured":bool(cfg.get("ELEVENLABS_API_KEY")),
        "alpha_requirements_implemented":False,
        "alpha_homologation_complete":False,
    }
    warnings=[]
    if not result["wayland_session"]:
        warnings.append("Sessão Wayland não detectada: homologação do desktop pendente.")
    if not result["gnome_session"]:
        warnings.append("GNOME não detectado: plataforma de homologação pendente.")
    if result["tts_local_enabled"]:
        warnings.append("TTS local habilitado; proibido no Alpha 0.1.")
    if not result["elevenlabs_key_configured"]:
        warnings.append("Chave ElevenLabs ausente: voz não pode ser validada.")
    if result["memory"].get("MemTotal_gib",8)<7.4:
        warnings.append("Memória física detectada abaixo do alvo de 8 GB.")
    result["warnings"]=warnings
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    result=check_environment()
    if args.json:
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    else:
        print("ADAM — pré-homologação (não é teste de funcionalidades)")
        for key in ("platform","python_version","session_type","desktop","memory"):
            print(f"{key}: {result[key]}")
        for warning in result["warnings"]:
            print("- "+warning)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
