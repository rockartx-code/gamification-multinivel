# Protocolo de la simulación — ronda 6 (marzo de 2027)

Mundo nuevo. Las rondas 1 a 5 (septiembre 2026 – enero 2027, 95 diarios, 30 personas) están archivadas en
`archivo/rondas-01-05-diarios-mensajes.zip`; sus conclusiones viven en `docs/qa/18` a `docs/qa/23`.
Nadie de aquellas rondas existe en este mundo: personal nuevo, clientes nuevos, catálogo con fichas
completas, tres sucursales con ciudad y la configuración encendida (paquetería simulada, secreto del
webhook, correo del corte).

Lo que cambia respecto a las rondas anteriores: **ya no basta con saber si algo funciona**. Esta ronda
mide **cuánto cuesta usarlo** y **cómo se siente**.

## Mundo

- Frontend real en `http://localhost:4321`, backend real (8 Lambdas) en `http://localhost:4400` sobre
  DynamoDB en memoria persistida. Correo interceptado (`leerCorreo`). Reloj simulado (`dia.sh`).
  Pasarela de pago simulada. Paquetería simulada encendida.
- Arranque: **2 de marzo de 2027**. Personal: Renata Bustos (gerente), Toño Vera (almacén),
  Mireya Solano (caja), Gaby Ledesma (coach), Alma Rentería (finanzas). Socia con red vacía:
  Paulina Ríos (código `PAULINA-PR`). Contraseñas en `credenciales.json`.
- Limitación conocida: Estadísticas (Athena) queda vacía.

## El reloj del navegador (guarda 15)

El mundo vive en 2027; la máquina que corre el arnés, no. Todo lo que la pantalla calcula con `new Date()`
—el mes contable, "días desde la última compra", el selector de meses del día de pago— saldría de un año
distinto al del backend, y la persona lo apuntaría como defecto del producto. Cuatro hallazgos de la ronda 6
eran exactamente eso: del arnés, no de la aplicación.

Por eso `abrirNavegador()` **pone el navegador en la hora del mundo** antes de abrir la página: lee
`GET /__sim/reloj` y lo fija con `ctx.clock.setSystemTime` (`sim/lib/persona.mjs`, `fijarRelojDelMundo()`).
La hora que quedó fijada se devuelve como `relojDelMundo` por si la persona la necesita.

- El reloj queda **corriendo**, no congelado: `setSystemTime` mueve el origen y el tiempo sigue fluyendo.
  `setFixedTime` e `install` lo detendrían, y con él los temporizadores de la aplicación.
- Si el mundo no da la hora, el arnés no se calla: lo anota en `consola` de la bitácora (`RELOJ: …`).
- `sim/comprobar.sh` lo verifica de verdad antes de cada ronda (`node sim/lib/comprobar-reloj.mjs`): abre un
  navegador, entra a la tienda, lee `new Date()` de la página y **falla si se desvía más de un día** del
  reloj del mundo o si el reloj está congelado. Abre **un solo** navegador y lo cierra; no deja bitácora ni
  perfil detrás.
- La fecha se mueve con `dia.sh`, como siempre. El navegador toma la hora **al abrirse**: si mueves el mundo
  a mitad de sesión, cierra y vuelve a abrir el navegador.

## Reglas para los agentes-persona

1. **Recibes solo tu historia y tu punto de entrada.** Ninguna instrucción de uso de la plataforma.
   Si no encuentras algo, no lo busques en el código: descríbelo como lo vive una persona real y sigue.
2. **Prohibido leer el código del repositorio.** Solo pantalla y correo.
3. **Un solo navegador a la vez** en todo el arnés (el contenedor se queda sin memoria con dos).
   Ábrelo con `abrirNavegador`, ciérralo con `cerrar()` al terminar.
4. Puedes mandar mensajes de WhatsApp a **Soporte Finding'U** (los clientes) o a tu **superior**
   (los empleados). Cada mensaje se registra con `bitacora.preguntar(...)` y se anota en `helpdesk.md`.
   Una pregunta no es un fracaso: es la medida de lo que la pantalla no explicó.
5. **Nada cuenta hasta verificarlo en pantalla.** Si dices "quedó guardado", recarga y compruébalo.
6. **La fecha de tu navegador es la del mundo, no la de la máquina** (arriba). Si una pantalla te muestra un
   año que no es el del mundo, es un hallazgo del producto: anótalo.

## Lo que hay que registrar (esto es la ronda)

Todo se registra con la bitácora del arnés (`sim/lib/persona.mjs`), que además **cuenta sola** los clics,
las teclas, las pantallas, las recargas y **cuánto tardaste en tocar algo después de que apareció cada
pantalla** (el tiempo de lectura antes de actuar).

```js
import { abrirNavegador, leer, controles, captura, leerCorreo, hoy } from '../sim/lib/persona.mjs';
const { pagina, bitacora: b, consola, cerrar } = await abrirNavegador({
  movil: true, perfil: 'mariana', persona: 'Mariana Robles, 29', rol: 'cliente',
});

b.tarea('comprar un bote de colágeno');          // lo que QUIERO, con mis palabras
b.pensar('creo que "PC" son puntos, pero…');      // lo que razono ANTES de actuar
b.duda('no sé si esto es una tienda o un negocio', '#/tienda');
b.atoron('le piqué a "Ver beneficios" y no pasó nada');
b.reintento('el código de recuperación ya no servía');
b.preguntar('soporte', '¿el envío es gratis o no?');   // o 'superior', 'patrocinadora', 'familiar'
b.sentir('frustración', 4, 'el envío gratis se volvió $129 al poner mi código postal');
await b.errores(pagina);                          // recoge los mensajes de error visibles
await b.lograr(pagina, { facilidad: 5, confianza: 4, comentario: '…' });
// o: await b.abandonar('no encontré dónde poner el cupón', pagina, { facilidad: 2 });
```

- `facilidad`: 1 (muy difícil) a 7 (muy fácil). Es la pregunta de siempre: *¿qué tan fácil fue esto?*
- `confianza`: 1 a 5. *¿Qué tan seguro estás de que de verdad quedó guardado?*
- Registra **una tarea por cada cosa que querías lograr**, aunque no la logres. El arnés cuenta cuántos
  clics, cuántas pantallas y cuántos segundos te costó cada una.
- `pensar()` es la cadena de pensamiento: escribe lo que estás razonando **antes** de actuar. El tiempo
  entre una llamada y la anterior es el que tardaste en entender la pantalla, y se guarda.

Al final, la opinión sobre cómo se ve y cómo se siente (todo 1 a 10 salvo lo indicado):

```js
b.opinar({
  primeraImpresion: 8, confianzaQueTransmite: 6, legibilidad: 7, coherencia: 7,
  sensacionMovil: 6,                       // null si no usaste celular
  tresAdjetivos: ['sobria', 'cara', 'fría'],
  mejorPantalla: 'la tienda', peorPantalla: 'el carrito en el celular',
  seParece: 'a una tienda de suplementos gringa, no a una app mexicana',
  recomendarias: 7,                        // 0 a 10
  volverias: 'sí, pero solo por el producto',
  comentario: 'se ve profesional pero no me habla a mí',
});
```

## Diario

Además de la bitácora, cada persona escribe `diarios/<nombre>-<fecha>.md` en primera persona:
hora, qué vio **textualmente**, qué hizo, qué sintió, qué le costó entender y qué reportaría.
Capturas en `capturas/`. El diario es la voz; la bitácora es la medida.

## Cómo se lee la ronda

`python3 sim/metricas.py` cruza todas las bitácoras: tabla por persona, tabla por tarea y totales
(clics por tarea lograda, segundos de reflexión, preguntas a soporte y a superiores, atorones,
reintentos, facilidad, confianza, estética). `python3 sim/cobertura.py` sigue midiendo qué rutas
tocó la ronda.

## Pasarela simulada y tareas programadas

| Acción | Qué simula |
|---|---|
| `POST /__sim/pago/<pedido>/confirmar` | La clienta paga y MercadoPago llama al webhook con el secreto. |
| `POST /__sim/pago/<pedido>/pagar-sin-aviso` | El pago se aprobó pero el webhook se perdió (para probar "Conciliar pagos"). |
| `POST /__sim/pago/<pedido>/reenviar-webhook` | Reintento de notificación (idempotencia). |

Al mover la fecha con `dia.sh`, el servidor dispara las tareas programadas que declaran los lambdas
(avisos de comisiones bloqueadas, rastreo y cierre de envíos, suscripciones, conciliación).
`POST /__sim/tareas` las dispara sin mover el reloj.
