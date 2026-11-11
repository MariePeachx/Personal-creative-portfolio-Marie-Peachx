"""Crea entradas del blog de viajes a partir de los vídeos de YouTube.

Lee el feed público del canal (no necesita claves) y, por cada vídeo que lleve
el hashtag #viajes, #viaje o #travel en el título o la descripción, crea un
archivo en _posts/ si todavía no existe.

Trucos para la descripción del vídeo en YouTube:
  - Una línea que empiece por 📍 indica el lugar.  Ejemplo:  📍 Lisboa, Portugal
  - La primera frase se usa como resumen de la entrada.
  - Las líneas que solo tienen hashtags no se copian al blog.

Uso:
  python youtube_a_blog.py                 # crea las entradas que falten
  python youtube_a_blog.py --prueba        # solo muestra lo que haría
  python youtube_a_blog.py --prueba --todos --salida carpeta   # prueba con todos los vídeos
"""
import argparse
import json
import os
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

CANALES = ["UCHzE-9M0bbHYNCtyb7x10KA"]  # Marie Peachx
HASHTAGS = {"#viajes", "#viaje", "#travel"}

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def leer_feed(canal):
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + canal
    req = urllib.request.Request(url, headers={"User-Agent": "blog-feed-reader"})
    with urllib.request.urlopen(req, timeout=30) as r:
        arbol = ET.fromstring(r.read())
    for e in arbol.findall("a:entry", NS):
        grupo = e.find("media:group", NS)
        yield {
            "id": e.findtext("yt:videoId", "", NS),
            "titulo": e.findtext("a:title", "", NS).strip(),
            "fecha": e.findtext("a:published", "", NS)[:10],
            "enlace": e.find("a:link", NS).get("href", ""),
            "descripcion": (grupo.findtext("media:description", "", NS) if grupo is not None else "").strip(),
        }


def es_de_viajes(v):
    texto = (v["titulo"] + " " + v["descripcion"]).lower()
    return any(h in re.findall(r"#\w+", texto) for h in HASHTAGS)


def ya_publicado(video_id, carpeta):
    if not os.path.isdir(carpeta):
        return False
    marca = "video: " + json.dumps(video_id)
    for nombre in os.listdir(carpeta):
        with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
            if marca in f.read():
                return True
    return False


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:60].rstrip("-") or "viaje"


def limpiar_titulo(t):
    t = re.sub(r"#\w+", "", t)
    return re.sub(r"\s{2,}", " ", t).strip(" |-·") or "Nueva aventura"


def crear_entrada(v):
    lugar = ""
    lineas = []
    for linea in v["descripcion"].splitlines():
        s = linea.strip()
        if s.startswith("📍"):
            lugar = s.lstrip("📍").strip()
            continue
        if s and all(p.startswith("#") for p in s.split()):
            continue  # línea solo de hashtags
        lineas.append(linea.rstrip())
    cuerpo = "\n".join(lineas).strip()
    cuerpo = re.sub(r"\n{3,}", "\n\n", cuerpo)
    resumen = re.split(r"(?<=[.!?])\s|\n", cuerpo, maxsplit=1)[0][:180] if cuerpo else ""

    cabecera = [
        "---",
        "title: " + json.dumps(limpiar_titulo(v["titulo"]), ensure_ascii=False),
        "date: " + v["fecha"],
    ]
    if lugar:
        cabecera.append("lugar: " + json.dumps(lugar, ensure_ascii=False))
    if resumen:
        cabecera.append("resumen: " + json.dumps(resumen, ensure_ascii=False))
    cabecera += [
        "portada: " + json.dumps("https://i.ytimg.com/vi/%s/hqdefault.jpg" % v["id"]),
        "video: " + json.dumps(v["id"]),
    ]
    if "/shorts/" in v["enlace"]:
        cabecera.append("video_vertical: true")
    cabecera += ["origen: youtube", "---", ""]

    texto = "\n".join(cabecera)
    if cuerpo:
        texto += "{% raw %}\n" + cuerpo + "\n{% endraw %}\n"
    nombre = "%s-%s.md" % (v["fecha"], slug(limpiar_titulo(v["titulo"])))
    return nombre, texto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", action="store_true", help="no escribe nada en _posts")
    ap.add_argument("--todos", action="store_true", help="ignora el filtro de hashtags (para probar)")
    ap.add_argument("--salida", help="carpeta donde escribir en modo prueba")
    a = ap.parse_args()

    posts = os.path.join(RAIZ, "_posts")
    destino = a.salida if a.prueba and a.salida else posts
    creadas = 0
    for canal in CANALES:
        for v in leer_feed(canal):
            if not (a.todos or es_de_viajes(v)) or ya_publicado(v["id"], posts):
                continue
            nombre, texto = crear_entrada(v)
            if a.prueba and not a.salida:
                print("== " + nombre + "\n" + texto)
            else:
                os.makedirs(destino, exist_ok=True)
                with open(os.path.join(destino, nombre), "w", encoding="utf-8", newline="\n") as f:
                    f.write(texto)
                print("Creada: " + nombre)
            creadas += 1
    print("Entradas nuevas: %d" % creadas)


if __name__ == "__main__":
    main()
