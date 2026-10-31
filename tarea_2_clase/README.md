# Del tablero al reel: incendios en el Perú 2026 en 45 segundos

Reel vertical con los hallazgos de la [tarea 3](../tarea_3/) ([dashboard](https://claude.ai/artifact/X8oDTiZ6w59yggsH36ptFu)).

- [reel/reel.mp4](reel/reel.mp4): el reel (45 s, 1080×1920)
- [reel/post.md](reel/post.md): texto del post, hashtags y aviso de IA
- [guion/guion.json](guion/guion.json): guion revisado, con la lista de correcciones

## Lo que corregí del guion

Qwen3.8 escribió el primer guion (6 escenas, cada una con frase, cifra y etiqueta). Lo revisé contra la fuente
antes de narrarlo:

- **Escena 3.** Qwen escribió *"Moquegua triplica su máximo"*. Es falso: el +337 % es contra el **promedio**
  2012–2025 (131 focos frente a un promedio de 30 y un máximo de 74). La frase quedó: *"El récord está en el sur
  andino: Moquegua cuadruplica su promedio, y Apurímac y Arequipa ya superan su máximo histórico."*
- **Escena 2.** "dieciseis" → "dieciséis".

Las cifras en pantalla estaban bien copiadas; el error estaba en la afirmación. Las cifras se pueden verificar
con código, pero las afirmaciones las tiene que revisar una persona.

## Uso de IA

Qwen3.8 escribió el primer guion, Qwen3-TTS generó la voz y MusicGen la música; el reel lo declara en pantalla y
en `post.md`. Claude me ayudó a escribir el código.
