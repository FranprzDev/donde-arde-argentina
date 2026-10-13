# Guía de estilo visual

El lenguaje visual por defecto (todo configurable en `theme:` del `story.yaml`).

## Principios

1. **Una sola visualización que se transforma.** Un mapa continuo: la cámara vuela, hace zoom, entra a una imagen
   satelital y vuelve. Nada de cortes a diapositivas.
2. **Una idea por escena.** Un número grande, una línea corta. Si hace falta explicar, es otra escena.
3. **El dato es la luz.** Fondo casi negro; lo único brillante es el dato (puntos, áreas, el número). El resto es contexto apagado.
4. **Escala humana y líneas de base.** «el doble que hace diez años», «3 de cada 10»: comparaciones que se entienden sin ejes.
5. **Legible en un celular**, en la primera vista, sin pausar (las reglas del harness lo garantizan).

## Color

| Rol | Clave de paleta | Valor por defecto | Uso |
|---|---|---|---|
| Fondo | `bg` | `#060609` | todo el fondo |
| Tierra | `land` | `#141316` | regiones del mapa |
| Vecinos | `neighbour` | `#0D0D11` | contexto fuera del área |
| Bordes | `border` | `#3E3C40` | límites, finos |
| Texto | `text` | `#F2F0EC` | titulares, números neutros |
| Texto secundario | `muted` | `#BEB6AC` | leyendas, fuentes |
| Acento | `accent` | `#FF6E1E` | la palabra clave, la segunda línea del título |
| Acento 2 | `accent2` | `#FFB03C` | encabezados mono, contornos resaltados, sublíneas |
| Caliente | `hot` | `#FFE2A0` | el número protagonista, contornos que brillan |
| Rojo | `red` | `#FF4028` | lo más grave / lo más reciente |
| Ceniza | `ash` | `#968E86` | áreas afectadas, lo que ya pasó |

Rampa de datos (`lut`): negro → bordó → naranja → ámbar → blanco cálido. Puntos y coropletas usan esa rampa;
cuanto más dato, más blanco. Para otros temas (agua, frío), cambiá `accent*` y `lut` a azules, manteniendo el contraste.

## Tipografía

| Rol | Fuente (OFL, incluida) | Tamaño (px a 1080p) |
|---|---|---|
| Titular / números | **Anton** (condensada, mayúsculas) | número 150 · titular 116–132 · cierre 110–124 · sublínea 66 · unidad 80 |
| Encabezados de escena | **JetBrains Mono** 800 | 52 |
| Leyendas, fuentes, rótulos | **Inter** 500–600 | 48 (mínimo absoluto) |

- Todo en el tercio izquierdo (x = 110 px); el mapa vive a la derecha. Una sombra suave oscurece la zona de texto.
- Mayúsculas para titulares y números; oración normal para fuentes y leyendas.
- Números en formato local (`es`: 12.345 · 12,5).

## Movimiento

- **Slam**: el texto entra grande (×1,45) y cae a su tamaño en ~0,28 s con un destello de glow; sale con un fade y un leve ascenso.
- **Números que cuentan** (`count_to`) aterrizan exactamente en el valor redondeado.
- **Cámara**: `zoomto` para acercarse a una región, `fly` entre regiones (baja el zoom lo justo para que se vean ambos extremos), `ease` para ajustes suaves.
- **Flash + golpe** en cada revelación importante; temblor (`shake`) solo en 2–3 momentos.
- **Glow/bloom** en datos y títulos clave; viñeta y grano de película fijos.

## Sonido

Drone grave + pads en loop, golpes (boom/taiko/braam) en cada revelación, whoosh en cada movimiento de cámara, tics por
año/región, un silencio corto antes de la frase de cierre. −14 LUFS.

## Qué evitar

- Más de ~12 palabras en pantalla a la vez, texto < 48 px, textos que duran menos de lo que se tarda en leerlos.
- Leyendas que no se explican («1 punto = 1 sismo» sí; un punto sin leyenda no).
- Fotos de stock, íconos decorativos, imágenes generadas por IA.
