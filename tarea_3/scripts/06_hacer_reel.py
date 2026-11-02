"""Paso 6 · reel/guion.json -> voz clonada -> reel vertical.

Basado en el flujo de la Sesión 15 del curso (reel.py). Se corre en el entorno `reel`:

    python scripts/06_hacer_reel.py --voz reel/recursos/mi_voz.m4a --autor "Nombre Apellido"

Guarda en reel/: reel.mp4, reel.wav, subtitulos.srt y portada.png.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf

import reel

BASE = Path(__file__).resolve().parents[1]
CARPETA = BASE / "reel"


def crear_musica(ruta, duracion, sr=44100):
    """Fondo suave hecho con código (cuatro acordes), así no hay licencia de terceros que declarar."""
    acordes = [[220.00, 261.63, 329.63], [174.61, 220.00, 261.63], [130.81, 196.00, 261.63], [196.00, 246.94, 293.66]]
    largo = 5.0
    t = np.arange(int(largo * sr)) / sr
    envolvente = np.sin(np.pi * t / largo) ** 0.6
    compases = []
    for acorde in acordes:
        s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) for f in acorde)
        compases.append(s * envolvente)
    pista = np.concatenate(compases * (int(duracion / (largo * len(acordes))) + 1))[: int(duracion * sr)]
    sf.write(ruta, 0.5 * pista / np.abs(pista).max(), sr)


p = argparse.ArgumentParser()
p.add_argument("--voz", required=True, help="15 a 25 s de tu voz: wav, m4a, ogg o mp3")
p.add_argument("--autor", required=True)
p.add_argument("--fuente", default="TSE e IBGE (Censo 2022)")
p.add_argument("--device", default="cuda", help="cuda o cpu")
p.add_argument("--tts", default=reel.TTS)
p.add_argument("--velocidad", type=float, default=1.05, help="1.05 = 5 %% más rápido, sin cambiar el tono")
a = p.parse_args()

t0 = time.time()
archivo = CARPETA / "guion.json"
guion = json.loads(archivo.read_text(encoding="utf-8"))
for e in guion["escenas"]:
    if not (CARPETA / e["imagen"]).exists():
        raise SystemExit(f"Falta {e['imagen']}: corre primero scripts/05_imagenes_reel.py en el entorno geo")

voz = reel.Voz(a.voz, modelo=a.tts, device=a.device)
reel._reloj(f"voz cargada; referencia: «{voz.texto_ref}»", t0)
narracion = reel.narrar(voz, guion, velocidad=a.velocidad)
archivo.write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
reel._reloj(f"narración: {narracion.duracion:.1f} s; WER por escena: "
            + ", ".join(f"{e['wer']:.2f}" for e in guion["escenas"]), t0)

reel.subtitulos(narracion, guion)
reel.a_srt(narracion, CARPETA / "subtitulos.srt")
reel._reloj(f"subtítulos: {len(narracion.palabras)} palabras", t0)

musica = CARPETA / "recursos" / "musica.wav"
crear_musica(musica, narracion.duracion + 1)
reel.portada(guion, narracion, CARPETA / "portada.png", a.fuente, a.autor)
reel.video(guion, narracion, CARPETA / "reel.mp4", a.fuente, a.autor, musica)
reel._reloj(f"listo: {CARPETA / 'reel.mp4'} ({narracion.duracion:.1f} s)", t0)
if not 45 <= narracion.duracion <= 75:
    print("¡Ojo! El reel debe durar entre 45 y 75 s: ajusta --velocidad.")
