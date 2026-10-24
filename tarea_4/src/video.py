"""Paso 5 del reel: Whisper marca el tiempo de cada palabra y Pillow + ffmpeg arman el video.

Cada escena muestra la imagen del dashboard que corresponde, la cifra y la etiqueta del guion
y los subtítulos palabra por palabra (la que suena va en naranja).
Salidas en reel/: reel.mp4 (1080x1920, 30 fps, H.264 + AAC, -14 LUFS), reel.srt, portada.png, post.md

Uso, desde la carpeta tarea_4:
    python src/video.py
"""
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pyloudnorm
import soundfile as sf
import torch  # noqa: F401  carga las DLL de CUDA (cuBLAS) que Whisper necesita en Windows
from faster_whisper import WhisperModel
from PIL import Image, ImageChops, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
GUION = RAIZ / "guion" / "guion.json"
VOZ = RAIZ / "voz"
IMAGENES = RAIZ / "imagenes"
MUSICA = RAIZ / "musica"
SALIDA = RAIZ / "reel"

W, H, FPS = 1080, 1920, 30
PAUSA = 0.5        # silencio entre escenas (s)
COLA = 1.5         # silencio al final, con la música saliendo (s)
LUFS = -14.0
DB_MUSICA = -16.0  # la música va 16 dB por debajo de la voz

FONDO = (23, 25, 28)
BLANCO = (245, 245, 245)
GRIS = (150, 155, 160)
NARANJA = (240, 116, 64)

# Zonas seguras: nada importante arriba de 200 px ni debajo de 1500 px (botones de las apps)
CAJA_IMG = (60, 250, W - 60, 1010)
Y_CIFRA, Y_ETIQUETA, Y_SUB = 1110, 1245, 1370

FUENTES = Path("C:/Windows/Fonts")
F_CIFRA = ImageFont.truetype(str(FUENTES / "seguibl.ttf"), 150)
F_ETIQUETA = ImageFont.truetype(str(FUENTES / "seguisb.ttf"), 54)
F_SUB = ImageFont.truetype(str(FUENTES / "segoeuib.ttf"), 58)
F_PEQUE = ImageFont.truetype(str(FUENTES / "seguisb.ttf"), 32)
F_TITULO = ImageFont.truetype(str(FUENTES / "seguibl.ttf"), 96)


def recortar(img):
    """Quita el fondo liso alrededor de la captura (toma el color de la esquina inferior derecha)."""
    fondo = Image.new(img.mode, img.size, img.getpixel((img.width - 1, img.height - 1)))
    bbox = ImageChops.difference(img, fondo).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    return img.crop(bbox) if bbox else img


def imagen_base(n):
    ruta = next(IMAGENES.glob(f"{n}_*.png"))
    img = recortar(Image.open(ruta).convert("RGB"))
    x0, y0, x1, y1 = CAJA_IMG
    escala = min((x1 - x0) / img.width, (y1 - y0) / img.height)
    # Se guarda un 8 % más grande para el acercamiento lento (efecto Ken Burns)
    return img.resize((round(img.width * escala * 1.08), round(img.height * escala * 1.08)), Image.LANCZOS)


def palabras_con_tiempo(whisper, ruta, frase, inicio):
    """Tiempos de Whisper con el texto del guion (Whisper puede escribir mal los nombres)."""
    a, sr = sf.read(ruta, dtype="float32")
    # Whisper espera 16 kHz; se remuestrea aquí porque PyAV 19 no funciona con faster-whisper 1.2
    a16 = np.interp(np.arange(0, len(a), sr / 16000), np.arange(len(a)), a).astype(np.float32)
    segs = whisper.transcribe(a16, language="es", word_timestamps=True)[0]
    oidas = [w for s in segs for w in s.words]
    texto = frase.split()
    if len(oidas) == len(texto):
        return [(t, inicio + w.start, inicio + w.end) for t, w in zip(texto, oidas)]
    # Si no coinciden, se reparte el tramo hablado según el largo de cada palabra
    a, b = (oidas[0].start, oidas[-1].end) if oidas else (0, sf.info(ruta).duration)
    pesos = np.cumsum([0] + [len(t) + 1 for t in texto]) / (sum(len(t) + 1 for t in texto))
    return [(t, inicio + a + (b - a) * p0, inicio + a + (b - a) * p1) for t, p0, p1 in zip(texto, pesos, pesos[1:])]


def bloques(palabras, max_chars=26):
    """Agrupa las palabras en líneas cortas de subtítulo."""
    out, actual = [], []
    for p in palabras:
        if actual and len(" ".join(w for w, _, _ in actual + [p])) > max_chars:
            out.append(actual)
            actual = []
        actual.append(p)
    if actual:
        out.append(actual)
    return out


def texto_centrado(d, y, texto, fuente, color):
    d.text((W / 2, y), texto, font=fuente, fill=color, anchor="mm")


def dibujar_sub(d, linea, t):
    total = d.textlength(" ".join(w for w, _, _ in linea), font=F_SUB)
    x = (W - total) / 2
    for w, a, b in linea:
        color = NARANJA if a <= t < b + 0.05 else BLANCO
        d.text((x, Y_SUB), w, font=F_SUB, fill=color, anchor="lm", stroke_width=4, stroke_fill=(0, 0, 0))
        x += d.textlength(w + " ", font=F_SUB)


def cuadro(escena, img, t, t0, t1, linea):
    lienzo = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(lienzo)
    d.text((60, 205), "INCENDIOS EN EL PERÚ · 2026", font=F_PEQUE, fill=GRIS, anchor="ls")
    d.text((W - 60, 205), "Voz generada con IA", font=F_PEQUE, fill=GRIS, anchor="rs")

    # Imagen: acercamiento de 1,00 a 1,08 y aparición suave en 0,3 s
    avance = (t - t0) / max(t1 - t0, 0.01)
    k = (1 + 0.08 * avance) / 1.08
    im = img.resize((round(img.width * k), round(img.height * k)), Image.BILINEAR)
    x0, y0, x1, y1 = CAJA_IMG
    pos = (round((x0 + x1 - im.width) / 2), round((y0 + y1 - im.height) / 2))
    alfa = min(1.0, (t - t0) / 0.3)
    if alfa < 1:
        im = Image.blend(Image.new("RGB", im.size, FONDO), im, alfa)
    lienzo.paste(im, pos)

    if escena["cifra"]:
        texto_centrado(d, Y_CIFRA, escena["cifra"], F_CIFRA, NARANJA)
        texto_centrado(d, Y_ETIQUETA, escena["etiqueta"], F_ETIQUETA, BLANCO)
    else:
        texto_centrado(d, Y_CIFRA, "Link en la bio", F_TITULO, NARANJA)
        texto_centrado(d, Y_ETIQUETA, escena["etiqueta"], F_ETIQUETA, BLANCO)
    if linea:
        dibujar_sub(d, linea, t)
    return lienzo


def leer_musica(nombre, sr):
    a, sr0 = sf.read(MUSICA / f"{nombre}.wav", dtype="float32")
    return np.interp(np.arange(0, len(a), sr0 / sr), np.arange(len(a)), a).astype(np.float32)


def alargar(a, n, xf):
    """Repite el clip con un fundido cruzado hasta llegar a n muestras."""
    out = a.copy()
    rampa = np.linspace(0, 1, xf, dtype=np.float32)
    while len(out) < n:
        out[-xf:] = out[-xf:] * (1 - rampa) + a[:xf] * rampa
        out = np.concatenate([out, a[xf:]])
    return out[:n]


def pista_musical(n, sr, cambio):
    """Parte tensa hasta `cambio` (s), fundido de 2 s y parte calma hasta el final."""
    xf, c = int(2 * sr), int(cambio * sr)
    tensa = alargar(leer_musica("tensa", sr), c + xf // 2, xf)
    calma = alargar(leer_musica("calma", sr), n - c + xf // 2, xf)
    musica = np.zeros(n, dtype=np.float32)
    tensa[-xf:] *= np.linspace(1, 0, xf)
    calma[:xf] *= np.linspace(0, 1, xf)
    musica[:len(tensa)] += tensa
    musica[c - xf // 2:] += calma[: n - (c - xf // 2)]
    musica[: sr] *= np.linspace(0, 1, sr)                      # entrada de 1 s
    musica[-int(2.5 * sr):] *= np.linspace(1, 0, int(2.5 * sr))  # salida de 2,5 s
    return musica


def srt_tiempo(s):
    ms = round(s * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    SALIDA.mkdir(exist_ok=True)
    guion = json.loads(GUION.read_text(encoding="utf-8"))
    pistas = json.loads((VOZ / "pistas.json").read_text(encoding="utf-8"))["pistas"]
    whisper = WhisperModel(str(RAIZ / "modelos" / "faster-whisper-large-v3-turbo"), device="cuda", compute_type="float16")

    # Audio: escenas con pausas, normalizado a -14 LUFS
    audios, escenas, t = [], [], 0.0
    for escena, pista in zip(guion["escenas"], pistas):
        ruta = VOZ / pista["archivo"]
        a, sr = sf.read(ruta, dtype="float32")
        palabras = palabras_con_tiempo(whisper, ruta, escena["frase"], t)
        fin = t + len(a) / sr + PAUSA
        escenas.append({"escena": escena, "t0": t, "t1": fin, "lineas": bloques(palabras)})
        audios += [a, np.zeros(int(PAUSA * sr), dtype="float32")]
        t = fin
    audios.append(np.zeros(int(COLA * sr), dtype="float32"))
    escenas[-1]["t1"] += COLA
    medidor = pyloudnorm.Meter(sr)
    voz = np.concatenate(audios)
    voz = pyloudnorm.normalize.loudness(voz, medidor.integrated_loudness(voz), LUFS)
    # La música cambia de tensa a calma cuando empieza la escena 5 ("viene la lluvia")
    cambio = escenas[min(4, len(escenas) - 1)]["t0"]
    musica = pista_musical(len(voz), sr, cambio)
    musica = pyloudnorm.normalize.loudness(musica, medidor.integrated_loudness(musica), LUFS + DB_MUSICA)
    audio = voz + musica
    audio = pyloudnorm.normalize.loudness(audio, medidor.integrated_loudness(audio), LUFS)
    audio = (np.tanh(audio / 0.95) * 0.95).astype(np.float32)  # limitador suave: sin picos recortados
    wav = SALIDA / "narracion.wav"
    sf.write(wav, audio, sr)
    duracion = len(audio) / sr

    # Subtítulos .srt
    srt, n = [], 0
    for e in escenas:
        for linea in e["lineas"]:
            n += 1
            srt.append(f"{n}\n{srt_tiempo(linea[0][1])} --> {srt_tiempo(linea[-1][2])}\n{' '.join(w for w, _, _ in linea)}\n")
    (SALIDA / "reel.srt").write_text("\n".join(srt), encoding="utf-8")

    # Video: Pillow dibuja cada cuadro y ffmpeg lo codifica junto con el audio
    ffmpeg = subprocess.Popen(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(SALIDA / "reel.mp4")],
        stdin=subprocess.PIPE)
    imgs = {i: imagen_base(i) for i in range(1, len(escenas) + 1)}
    for f in range(int(duracion * FPS)):
        t = f / FPS
        i, e = next((i, e) for i, e in enumerate(escenas, 1) if t < e["t1"] or i == len(escenas))
        # La línea visible es la que está sonando; en las pausas queda la última dicha
        dichas = [l for l in e["lineas"] if l[0][1] <= t]
        linea = dichas[-1] if dichas else None
        ffmpeg.stdin.write(cuadro(e["escena"], imgs[i], t, e["t0"], e["t1"], linea).tobytes())
    ffmpeg.stdin.close()
    ffmpeg.wait()
    wav.unlink()

    # Portada y texto del post
    portada = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(portada)
    base = imagen_base(1)
    portada.paste(base, (round((W - base.width) / 2), 300))
    for k, linea in enumerate(["¿2026, año récord", "de incendios?"]):
        texto_centrado(d, 1250 + k * 115, linea, F_TITULO, BLANCO if k == 0 else NARANJA)
    texto_centrado(d, 1500, "Lo que dicen los satélites", F_ETIQUETA, GRIS)
    portada.save(SALIDA / "portada.png")

    post = (f"{guion['texto_post']}\n\n{' '.join(guion['hashtags'])}\n\n"
            "Voz generada con IA (Qwen3-TTS) a partir de la voz del autor. Música generada con IA (MusicGen).\n")
    (SALIDA / "post.md").write_text(post, encoding="utf-8")
    print(f"Reel: {SALIDA / 'reel.mp4'} ({duracion:.1f} s)")


if __name__ == "__main__":
    main()
