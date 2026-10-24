"""Música de fondo instrumental con MusicGen (modelo abierto de Meta), en dos partes que siguen el guion:

    tensa.wav  escenas 1-4: récord de octubre, sur andino, área quemada
    calma.wav  escenas 5-6: viene la lluvia y cierre

Uso, desde la carpeta tarea_4:
    python src/musica.py
"""
from pathlib import Path

import soundfile as sf
import torch
from huggingface_hub import snapshot_download
from transformers import AutoProcessor, MusicgenForConditionalGeneration

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "musica"
MODELO = "facebook/musicgen-medium"
SEGUNDOS = 30  # MusicGen se entrenó con clips de 30 s; video.py los encadena

PIEZAS = {
    "tensa": "instrumental cinematic documentary underscore, tense and urgent, low pulsing strings, "
             "deep piano notes, soft taiko drums, minor key, 90 bpm, no vocals",
    "calma": "instrumental cinematic documentary underscore, calm and hopeful, gentle piano, "
             "warm strings, soft rain ambience, major key, 80 bpm, no vocals",
}


def main():
    SALIDA.mkdir(exist_ok=True)
    # Carpeta local: en Windows sin permisos de symlink la caché de HF falla
    ruta = snapshot_download(MODELO, local_dir=RAIZ / "modelos" / MODELO.split("/")[-1])
    proc = AutoProcessor.from_pretrained(ruta)
    modelo = MusicgenForConditionalGeneration.from_pretrained(ruta, torch_dtype=torch.float16).to("cuda")
    sr = modelo.config.audio_encoder.sampling_rate
    tokens = int(SEGUNDOS * modelo.config.audio_encoder.frame_rate)

    for nombre, prompt in PIEZAS.items():
        torch.manual_seed(7)
        entrada = proc(text=[prompt], return_tensors="pt").to("cuda")
        audio = modelo.generate(**entrada, do_sample=True, guidance_scale=3.0, max_new_tokens=tokens)
        sf.write(SALIDA / f"{nombre}.wav", audio[0, 0].float().cpu().numpy(), sr)
        print(f"{nombre}.wav: {audio.shape[-1] / sr:.1f} s")


if __name__ == "__main__":
    main()
