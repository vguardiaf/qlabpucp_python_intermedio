"""Paso 4 del reel: Qwen3-TTS narra cada escena del guion con la voz clonada del autor.

1. Convierte guion/Audio.ogg a WAV y se queda con ~15 s cortados en una pausa.
2. Whisper transcribe esa referencia (Qwen3-TTS necesita el texto de lo que se dice).
3. Qwen3-TTS genera una pista por escena. Whisper la vuelve a escuchar y, si entiende mal
   más del 25 % de las palabras, la genera de nuevo (hasta 3 intentos).

Uso, desde la carpeta tarea_4:
    python src/voz.py
"""
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import jiwer
import numpy as np
import soundfile as sf
import torch
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from qwen_tts import Qwen3TTSModel

RAIZ = Path(__file__).resolve().parents[1]
GUION = RAIZ / "guion" / "guion.json"
AUDIO = RAIZ / "guion" / "Audio.ogg"
SALIDA = RAIZ / "voz"
MODELOS = RAIZ / "modelos"

TTS = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
WHISPER = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"


def modelo_local(repo):
    """Descarga a tarea_4/modelos: en Windows sin permisos de symlink la caché de HF falla."""
    return snapshot_download(repo, local_dir=MODELOS / repo.split("/")[-1])
REFERENCIA_MAX_SEG = 16
WER_MAX = 0.25
INTENTOS = 3


def a_wav(origen, destino, hasta=None):
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(origen), "-ac", "1", "-ar", "24000"]
    if hasta:
        cmd += ["-t", f"{hasta:.2f}"]
    subprocess.run(cmd + [str(destino)], check=True)


def audio_16k(ruta):
    """Audio para Whisper decodificado con ffmpeg (PyAV 19 no es compatible con faster-whisper 1.2)."""
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(ruta), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def normalizar(s):
    return jiwer.RemovePunctuation()(s.lower()).split()


def wer(esperado, oido):
    return jiwer.wer(" ".join(normalizar(esperado)), " ".join(normalizar(oido)) or "-")


def main():
    SALIDA.mkdir(exist_ok=True)
    guion = json.loads(GUION.read_text(encoding="utf-8"))
    whisper = WhisperModel(modelo_local(WHISPER), device="cuda", compute_type="float16")

    # 1-2. Referencia: segmentos completos de Whisper hasta ~16 s
    completo = SALIDA / "referencia_completa.wav"
    a_wav(AUDIO, completo)
    segmentos = list(whisper.transcribe(audio_16k(completo), language="es")[0])
    elegidos = [s for s in segmentos if s.end <= REFERENCIA_MAX_SEG] or segmentos[:1]
    ref_wav = SALIDA / "referencia.wav"
    a_wav(AUDIO, ref_wav, hasta=elegidos[-1].end + 0.2)
    ref_texto = " ".join(s.text.strip() for s in elegidos)
    completo.unlink()
    print(f"Referencia: {elegidos[-1].end:.1f} s -> {ref_texto!r}")

    # 3. Narración por escena
    tts = Qwen3TTSModel.from_pretrained(modelo_local(TTS), device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
    prompt_voz = tts.create_voice_clone_prompt(ref_audio=str(ref_wav), ref_text=ref_texto)

    pistas = []
    for i, escena in enumerate(guion["escenas"], 1):
        for intento in range(1, INTENTOS + 1):
            wavs, sr = tts.generate_voice_clone(text=escena["frase"], language="Spanish", voice_clone_prompt=prompt_voz)
            ruta = SALIDA / f"escena_{i}.wav"
            sf.write(ruta, wavs[0], sr)
            oido = " ".join(s.text for s in whisper.transcribe(audio_16k(ruta), language="es")[0])
            error = wer(escena["frase"], oido)
            print(f"Escena {i}, intento {intento}: {len(wavs[0]) / sr:.1f} s, WER {error:.0%}")
            if error <= WER_MAX:
                break
        pistas.append({"escena": i, "archivo": ruta.name, "duracion_seg": round(len(wavs[0]) / sr, 2),
                       "wer": round(error, 3), "intentos": intento, "whisper_oyo": oido.strip()})

    total = sum(p["duracion_seg"] for p in pistas)
    (SALIDA / "pistas.json").write_text(
        json.dumps({"modelo": TTS, "referencia_texto": ref_texto, "duracion_total_seg": round(total, 1),
                    "pistas": pistas}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Narración: {total:.1f} s en {len(pistas)} pistas -> {SALIDA}")


if __name__ == "__main__":
    main()
