"""Arranca 360 Analytics con un solo comando: python iniciar.py

Pasos automaticos: localiza uv (lo instala con pip si falta), instala las
dependencias de Python (sin PyTorch, que la web no necesita), compila la web
si hace falta, abre el navegador y lanza el servidor. Solo usa la libreria
estandar, asi que funciona con cualquier Python 3.8+.
"""
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DIST = WEB / "dist" / "index.html"
PORT = int(os.environ.get("PORT", "8501"))
URL = f"http://localhost:{PORT}"
WIN = os.name == "nt"


def paso(msg):
    print(f"\n==> {msg}", flush=True)


def fallo(msg):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, cwd=ROOT):
    # En Windows npm es un .cmd y necesita shell.
    if subprocess.call(cmd, cwd=cwd, shell=WIN and cmd[0] == "npm") != 0:
        fallo("fallo el comando: " + " ".join(map(str, cmd)))


def ensure_uv():
    uv = shutil.which("uv")
    if uv:
        return [uv]
    paso("uv no esta instalado: instalando con pip")
    if subprocess.call([sys.executable, "-m", "pip", "install", "--user", "uv"]) != 0:
        fallo("no se pudo instalar uv. Instalalo desde https://docs.astral.sh/uv/")
    uv = shutil.which("uv")
    return [uv] if uv else [sys.executable, "-m", "uv"]


def build_web(uv):
    if DIST.exists():
        return
    if shutil.which("npm"):
        npm = ["npm"]
    else:
        # Sin Node.js: uv descarga uno portable (paquete PyPI) en un entorno temporal.
        paso("Node.js no encontrado: usando Node portable via uv")
        npm = uv + [
            "run", "--no-project", "--with", "nodejs-wheel-binaries>=22,<23",
            "python", "-c",
            "import sys, nodejs_wheel.executable as e; sys.exit(e.npm(sys.argv[1:]))",
        ]
    paso("Compilando la web (solo la primera vez)")
    run(npm + ["ci" if (WEB / "package-lock.json").exists() else "install"], cwd=WEB)
    run(npm + ["run", "build"], cwd=WEB)


def open_when_ready():
    for _ in range(120):
        try:
            urllib.request.urlopen(f"{URL}/api/health", timeout=1)
            webbrowser.open(URL)
            return
        except Exception:
            time.sleep(0.5)


def main():
    os.chdir(ROOT)
    uv = ensure_uv()
    paso("Instalando dependencias de Python (sin PyTorch)")
    run(uv + ["sync", "--inexact", "--no-install-package", "torch"])
    build_web(uv)
    paso(f"Servidor en {URL}  (Ctrl+C para detener)")
    threading.Thread(target=open_when_ready, daemon=True).start()
    try:
        subprocess.call(uv + ["run", "--no-sync", "uvicorn", "services.web:app", "--port", str(PORT)])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
