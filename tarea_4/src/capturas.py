"""Captura del dashboard de la tarea 3 una imagen por escena del guion.

Usa Microsoft Edge (ya instalado en Windows) a través de Playwright, en modo oscuro.
Uso, desde la carpeta tarea_4:
    python src/capturas.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
DASHBOARD = RAIZ.parent / "tarea_3" / "docs" / "index.html"
SALIDA = RAIZ / "imagenes"

SUR_ANDINO = ["Apurímac", "Arequipa", "Moquegua"]  # los que nombra la escena 3


def capas(page, anom, focos, inc):
    # Los controles están ocultos, así que se cambian por código y no con clics
    page.evaluate("""(estado) => Object.entries(estado).forEach(([id, on]) => {
        const el = document.getElementById(id);
        el.checked = on;
        el.dispatchEvent(new Event("change"));
    })""", {"capa-anom": anom, "capa-focos": focos, "capa-inc": inc})
    page.wait_for_timeout(300)


def main():
    SALIDA.mkdir(exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="msedge")
        page = nav.new_page(viewport={"width": 900, "height": 1600}, device_scale_factor=2,
                            color_scheme="dark", reduced_motion="reduce")
        page.goto(DASHBOARD.as_uri(), wait_until="networkidle")
        page.wait_for_timeout(1000)
        # Los controles del mapa no sirven en un video
        page.add_style_tag(content=".chip-toggle, #mapa-reset { visibility: hidden; }")

        # Escena 1 y 2: gráficos de octubre y de la temporada acumulada (con su título)
        page.locator("#g-oct").locator("xpath=..").screenshot(path=SALIDA / "1_octubre.png")
        page.locator("#g-acum").locator("xpath=..").screenshot(path=SALIDA / "2_temporada.png")

        # Escena 3: anomalía por departamento, con zoom al sur andino
        capas(page, anom=True, focos=False, inc=False)
        page.evaluate("""(nombres) => {
            const fs = DATOS.geo.features.filter(f => nombres.includes(f.properties.departamento));
            const b = fs.map(f => rutaGeo.bounds(f));
            zoomA([[Math.min(...b.map(x => x[0][0])), Math.min(...b.map(x => x[0][1]))],
                   [Math.max(...b.map(x => x[1][0])), Math.max(...b.map(x => x[1][1]))]], 6);
        }""", SUR_ANDINO)
        page.wait_for_timeout(1200)
        # Nombres de los departamentos, con tamaño fijo en pantalla aunque el mapa tenga zoom
        page.evaluate("""(nombres) => {
            const k = d3.zoomTransform(svgMapa.node()).k;
            DATOS.geo.features.filter(f => nombres.includes(f.properties.departamento)).forEach(f => {
                const [x, y] = rutaGeo.centroid(f);
                gMapa.append("text").attr("x", x).attr("y", y).attr("text-anchor", "middle")
                    .attr("font-size", 15 / k).attr("font-weight", 700).attr("fill", "#fff")
                    .attr("stroke", "#000").attr("stroke-width", 3 / k).attr("paint-order", "stroke")
                    .text(f.properties.departamento);
            });
        }""", SUR_ANDINO)
        page.locator("#mapa").screenshot(path=SALIDA / "3_sur_andino.png")
        page.evaluate("() => gMapa.selectAll('text').remove()")

        # Escena 4: tarjeta Sentinel-2 del incendio más grande de Arequipa
        page.locator(".dnbr-card", has_text="Arequipa").first.screenshot(path=SALIDA / "4_arequipa_dnbr.png")

        # Escena 5: incendios activos coloreados por riesgo, todo el Perú
        page.evaluate("() => document.getElementById('mapa-reset').click()")
        capas(page, anom=False, focos=False, inc=True)
        page.wait_for_timeout(1200)
        page.locator("#mapa").screenshot(path=SALIDA / "5_riesgo.png")

        # Escena 6: portada del dashboard con los hallazgos
        page.locator("#hallazgos").screenshot(path=SALIDA / "6_dashboard.png")
        nav.close()
    print("Imágenes en", SALIDA)


if __name__ == "__main__":
    main()
