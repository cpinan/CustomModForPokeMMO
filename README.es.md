# CustomModForPokeMMO

*[English version](README.md)*

Mods para [PokeMMO](https://pokemmo.com), construidos y verificados contra la
revisión de cliente **32920** (revisión de tema 8). Dos de ellos corrigen fallos
reales que aparecen en dispositivos Android; el resto son cosméticos.

Todos se probaron en hardware real — una Retroid Pocket G2 con Android 15 —
leyendo el propio mensaje `layout loop detected` del cliente desde logcat, no
mirando la interfaz a ojo.

---

## Los mods

### `android-layout-fix` — elimina el aviso de "UI layout loop"

El tema Android que trae PokeMMO le da a un widget dos límites de ancho que se
contradicen. En `data/themes/android/ui/android-settings.xml`:

```xml
<theme name="settings-scrollpane" ref="scrollpane">
    <param name="minWidth"><int>1080</int></param>
    <param name="maxWidth"><int>800</int></param>
```

Los dos valores parecen estar intercambiados. El que realmente rompe las cosas
es el **mínimo**: 1080px es más ancho de lo que ese widget puede llegar a
recibir una vez que se descuentan la barra de pestañas y los bordes. El cálculo
de la disposición nunca se estabiliza, así que TWL (la librería de interfaz) lo
reintenta un número fijo de veces, se rinde, y escribe `layout loop detected`.
El cliente lo muestra como *"A UI layout loop issue was detected. You may
experience reduced performance or lag."*

Abrir **Ajustes** lo dispara siempre.

Este mod incluye por ruta absoluta los 51 archivos del tema original y
reemplaza exactamente uno, con los límites corregidos a `min 800 / max 1080`.
Como todo lo demás se toma directamente de `/data/themes/android/`, las
actualizaciones del cliente al resto del tema siguen aplicándose.

Verificado por eliminación:

| `settings-scrollpane` | resultado en el dispositivo |
|---|---|
| `min 1080 / max 800` (original) | se cicla |
| `min 1080 / max 32767` | sigue ciclándose — así que `min > max` no era la causa |
| `min 500 / max 32767` | sin ciclo, pero los controles quedan aplastados |
| **`min 800 / max 1080`** | **sin ciclo y la interfaz se ve correcta** |

**Instalación:** impórtalo y luego elige *Android Layout Fix* en
**Ajustes → Interfaz → Tema**, y reinicia.

### `region-label-unpad` — corrige el ciclo de la Pokédex en Sinnoh y Unova

Este no es un fallo del cliente. [SupersStrings](https://forums.pokemmo.com/index.php?/topic/188112-supersstrings/)
redefine los nombres de las cinco regiones como etiquetas de dos líneas
rellenadas con 19 caracteres `▁`, para que los botones de región midan más
ancho:

```xml
<string id="250003">[ Sinnoh ]\n▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁</string>
```

Esa etiqueta rellenada desestabiliza la disposición de la Pokédex, y solo en las
regiones cuyo contenido ya estaba cerca del límite — por eso Sinnoh y Unova se
ciclan mientras Kanto, Hoenn y Johto funcionan bien.

Además, esos ids no son etiquetas privadas de botones. El cliente los sustituye
como `{STRING_250000}`…`{STRING_250004}` dentro de frases normales — *"A ticket
required to sail between the {STRING_250000} and {STRING_250001} regions"* — así
que los corchetes y los bloques acaban también en las descripciones de objetos.

Este mod devuelve los nombres simples y no cambia nada más. SupersStrings sigue
funcionando; lo único que pierdes son los botones de región más anchos.

**Instalación:** tiene que cargarse **después** de SupersStrings — usa la flecha
hacia abajo en Administración de Mods para colocarlo debajo, y reinicia.

### `only-shiny-sprites` — oculta a todos los que no son shiny en combate

El cliente distingue normal de shiny solo por el nombre del archivo —
`25-front-n.png` frente a `25-front-s.png` — así que este mod incluye un PNG
totalmente transparente para cada archivo `-n` de la dex de la gen 1–5, de
frente y de espalda, incluidas las variantes por género `-m`/`-f`. Son 3.894
archivos con los mismos pocos bytes transparentes, por eso el archivo final pesa
menos de 900 KB.

**No** incluye ningún archivo `-s`. Los shiny no se sobrescriben, se toman del
sprite de la ROM y se ven igual que siempre. Los encuentros normales no dibujan
nada, así que un shiny es imposible de pasar por alto.

Tu propio Pokémon también queda oculto — borra `*-back-n*.png` y vuelve a
compilar si prefieres seguir viendo tu lado. Cubre los ids 1–649; las formas
alternativas y los disfraces de evento usan ids más altos y no se ocultan.

### `shiny-scale-probe` — una prueba desechable

Incluye solo las tres tablas de escala, sin sprites, con valores exagerados a
propósito para especies comunes de las primeras rutas (algunas en `1`, otras en
`4`, frente al valor por defecto de `3`). Un solo encuentro salvaje responde si
las tablas de escala afectan a sprites que el mod **no** ha reemplazado — eso
decide si "hacer los shiny más grandes" son diez líneas de texto o descargar un
sprite por especie. Bórralo cuando tengas la respuesta.

### `stadium-battlesprites` — sprites de combate de Pokémon Stadium 2

299 GIFs animados, de frente y de espalda, con una tabla de escala por especie.

> Renderizados a partir de modelos extraídos de Pokémon Stadium 2. Asegúrate de
> estar cómodo redistribuyéndolos antes de publicar esta carpeta en otro sitio.

### `demo-strings` — un ejemplo

Cambia dos etiquetas de menú. Sirve únicamente como plantilla para ver cómo se
arma un mod de textos.

---

## Cómo instalar cualquiera de ellos

1. Descarga el `.mod` desde `dist/`.
2. En PokeMMO abre **Administración de Mods** — desde el menú de la pantalla de
   inicio de sesión en PC, o el menú de las tres rayas en Android.
3. **Importar Mod** y elige el archivo, o **Abrir la carpeta de Mods** y arrástralo.
4. Marca **Activar**, guarda y reinicia el cliente.
5. Los mods de tema además hay que seleccionarlos en **Ajustes → Interfaz →
   Tema**, y reiniciar otra vez.

## Compilar desde el código

Cada carpeta dentro de `mods/` es el archivo tal y como lo lee el cliente.
Comprime el **contenido** de la carpeta, no la carpeta en sí — si no, `info.xml`
queda un nivel más abajo y el cliente no listará el mod.

## Compatibilidad

Compilado contra la revisión de cliente 32920 / revisión de tema 8. Un tema
hecho para una revisión más nueva es rechazado directamente, así que si una
actualización rompe alguno de estos, mira `Client Theme Revision` al principio
de `log/mods.log` y vuelve a basarlo.

## Créditos

* SupersStrings, de **superworldsun** — `region-label-unpad` existe para
  acompañarlo, no para reemplazarlo.
* El patrón de includes absolutos para temas viene de
  [pokemmo-port-themes](https://github.com/CodesNL/pokemmo-port-themes).

## Sin relación con PokeMMO

Son modificaciones no oficiales. Los desarrolladores no respaldan los añadidos
de terceros; instálalos bajo tu propio riesgo y solo desde fuentes de confianza.
