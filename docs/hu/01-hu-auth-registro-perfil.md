# Finding'U — Historias de Usuario: Autenticación, Registro y Perfil

> **Propósito:** Documentar, mediante ingeniería inversa del código fuente, las Historias de
> Usuario (HU) que describen el comportamiento **real implementado** del dominio Autenticación,
> Registro de cuenta y Perfil de usuario. Sirve como insumo para diseño/ejecución de pruebas y
> para detectar brechas entre lo que el frontend espera del backend y lo que el backend
> efectivamente implementa.
>
> **Fecha:** 2026-08-01
> **Método:** Ingeniería inversa de código (`gamificacion-multinivel-f/src/app/**`,
> `gamificacion-multinivel-f/lambda/handler.py`) + revisión cruzada contra
> `docs/qa/01-funcionalidades-sistema.md` y `docs/qa/02-matriz-pruebas-e2e.md`. Donde el código
> difiere de lo que documentan esos dos archivos (que citan mayormente `Micro-lambda-GMF/python/auth_utils.py`,
> un backend distinto al que consume realmente el frontend), se documenta el comportamiento
> **observado en el código que el frontend invoca** (`gamificacion-multinivel-f/lambda/handler.py`)
> y se deja constancia de la divergencia en la sección "Observaciones para QA".
>
> Las HU reflejan comportamiento real (bugs, huecos y atajos incluidos), no comportamiento deseado.

---

## Tabla resumen

| ID HU | Título | Prioridad | IDs E2E vinculados |
|---|---|---|---|
| HU-AUTH-01 | Registro de cuenta (datos básicos, validación y duplicado de correo) | Alta | E2E-REF-01, E2E-REF-08 |
| HU-AUTH-02 | Vinculación con patrocinador al registrarse | Alta | E2E-REF-01 a 07, E2E-REF-11 a 13 |
| HU-AUTH-03 | Pantalla de "verificación pendiente" tras registro | Media | SIN COBERTURA EN MATRIZ |
| HU-AUTH-04 | Verificación de email vía enlace (`/verificar-email`) | Alta | E2E-AUTH-14, E2E-AUTH-15, E2E-AUTH-16 |
| HU-AUTH-05 | Login con redirección por rol | Crítica | E2E-AUTH-01, E2E-AUTH-02 |
| HU-AUTH-06 | Validaciones y errores en el formulario de login | Alta | E2E-AUTH-03, E2E-AUTH-06, E2E-AUTH-07 |
| HU-AUTH-07 | Bloqueo por email no verificado y reenvío de confirmación | Alta | E2E-AUTH-04, E2E-AUTH-05 |
| HU-AUTH-08 | Solicitud de recuperación de contraseña (OTP) | Alta | E2E-AUTH-08, E2E-AUTH-09 |
| HU-AUTH-09 | Restablecer contraseña con OTP | Alta | E2E-AUTH-10, E2E-AUTH-11, E2E-AUTH-12, E2E-AUTH-13 |
| HU-AUTH-10 | Cambio de contraseña autenticado desde el perfil | Media | E2E-AUTH-17, E2E-AUTH-18, E2E-AUTH-19 |
| HU-AUTH-11 | Control de acceso por rol (guards) | Alta | E2E-AUTH-20, E2E-AUTH-21 |
| HU-AUTH-12 | Persistencia de sesión y cierre de sesión (logout) | Media | E2E-AUTH-22 |
| HU-AUTH-13 | Edición de datos personales del perfil | Media | E2E-PROF-01 |
| HU-AUTH-14 | Registro y actualización de CLABE interbancaria | Alta | E2E-PROF-02, E2E-PROF-03 |
| HU-AUTH-15 | Carga de documentos propios (constancia/INE/CURP) | Media | E2E-PROF-04, E2E-PROF-05 |
| HU-AUTH-16 | Visualización de los datos del patrocinador | Media | E2E-PROF-06, E2E-REF-03 |
| HU-AUTH-17 | Aviso de privacidad en primer acceso (funcionalidad ausente) | Baja | E2E-PROF-07, E2E-NOTI-06 |
| HU-AUTH-18 | Direcciones de envío del cliente (gestión fuera del perfil) | Media | SIN COBERTURA EN MATRIZ (perspectiva perfil; ver E2E-CART-10) |

18 Historias de Usuario. 2 sin ningún ID de la matriz E2E que las cubra directamente.

---

### HU-AUTH-01 — Registro de cuenta (datos básicos, validación y duplicado de correo)
**Como** visitante interesado en unirme a Finding'U **quiero** crear una cuenta con mis datos básicos **para** acceder a la plataforma como cliente/asociado.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado el formulario de registro (landing o tienda), cuando falta nombre, apellido paterno, apellido materno, correo o contraseña, entonces se marca el campo específico en rojo con mensaje ("El nombre es obligatorio.", etc.) y no se envía la solicitud (`landing.component.ts:262-272`).
- Dado que la contraseña y su confirmación no coinciden, cuando se envía el formulario, entonces se muestra "Las contraseñas no coinciden." en el campo de confirmación y se bloquea el envío (`landing.component.ts:273-276`); el backend valida lo mismo de forma redundante (`handler.py:4072-4073`).
- Dado un correo válido y datos completos, cuando se envía el formulario, entonces se llama `POST {baseUrl}/auth/crearcuenta` con `name` (concatenación de nombre + apellidos), `email`, `phone`, `password`, `confirmPassword`, `referralToken`, `productId` (`landing.component.ts:278-289`).
- Dado un correo ya registrado (como `AUTH` o como `CUSTOMER`), cuando se intenta crear la cuenta, entonces el backend responde `{"message": "El correo ya esta registrado. Intenta usar recuperar contrasena.", "Error": "Conflict"}` con **HTTP 200** (no 409) y el frontend lo traduce a error visible (`handler.py:4078-4079`; `real-api.service.ts:161-172`).
- Dado un registro exitoso, cuando el backend crea el `CUSTOMER`, entonces por defecto se le asigna `isAssociate=true`, `canAccessAdmin=false`, `activeBuyer=false`, `discountRate=0` y privilegios normalizados vacíos (`handler.py:4088-4097`).
- El `customerId` se genera como timestamp en milisegundos si no viene en el payload (`handler.py:4081`), no como contador secuencial.
- El envío del correo de bienvenida es "best effort": si falla el envío (SES), el registro igual se considera exitoso y solo se loggea el error (`handler.py:4105-4108`).

**Fuente (código):** `gamificacion-multinivel-f/src/app/pages/landing/landing.component.ts:258-324`, `landing.component.html:463-553`; `gamificacion-multinivel-f/lambda/handler.py:4066-4125`; `real-api.service.ts:139-174`
**Cobertura E2E:** E2E-REF-01 (registro con patrocinador), E2E-REF-08 (email duplicado). No hay caso dedicado a "contraseñas no coinciden en registro" en la matriz.

---

### HU-AUTH-02 — Vinculación con patrocinador al registrarse
**Como** visitante que llega desde el enlace de un patrocinador **quiero** que mi cuenta quede vinculada a esa persona **para** que ambos recibamos los beneficios de la red.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que se visita `/landing/:idSponsor`, cuando la página carga, entonces el `idSponsor` de la URL se guarda en `localStorage['leaderId']` y se usa como `referralToken` al registrarse, incluso si el usuario cierra y reabre la landing más tarde sin el parámetro (`landing.component.ts:122-129`).
- Dado que no hay token en la ruta, cuando se muestra el formulario, entonces aparece un campo opcional "Código de Referido" (`referralCodeInput`) que el usuario puede llenar manualmente (`landing.component.html:540-545`); si hay token en la ruta, este campo **no se muestra**.
- El "token de referido" real es el **`customerId` numérico crudo del patrocinador**, no un código alfanumérico tipo `{Nombre}-{Iniciales}`: `_resolve_leader_id` solo hace `_get_by_id("CUSTOMER", lid)` con el valor recibido, sin ninguna tabla de resolución de códigos de referido (`handler.py:395-400`).
- Dado un `referralToken`/código manual que no corresponde a ningún `customerId` existente, cuando se registra la cuenta, entonces `_resolve_leader_id` retorna `None` **silenciosamente** y la cuenta se crea **sin patrocinador**, sin ningún mensaje de error al usuario (`handler.py:4083`, `395-400`).
- Dado un registro con patrocinador válido, cuando se crea la cuenta, entonces `leaderId` queda persistido en el `CUSTOMER` (`handler.py:4091`) y, si el patrocinador tiene correo, recibe una notificación "Nuevo miembro en tu red" (`handler.py:4109-4115`, `1050-1067`); si el envío falla, el registro no se revierte (best effort).
- Dado un registro sin token ni código manual, cuando se envía, entonces la cuenta se crea con `leaderId=None` sin bloquear el registro (registro "directo").
- La landing muestra datos públicos del patrocinador (nombre, WhatsApp) resolviendo el `idSponsor` de la ruta contra `GET /referrer/{id}`, que también asume que el id es el `customerId` numérico (`handler.py:1100-1106`; `landing.component.ts:352-363`). Si el id no es numérico o no existe, el patrocinador simplemente no se muestra (`hasRealSponsor=false`), sin error visible.

**Fuente (código):** `landing.component.ts:122-131, 231-247, 352-363`; `handler.py:395-400, 1100-1106, 4082-4115`
**Cobertura E2E:** E2E-REF-01, E2E-REF-02, E2E-REF-03, E2E-REF-04, E2E-REF-05, E2E-REF-06 (el "mensaje de código inválido" que espera este caso **no existe**: ver Observaciones), E2E-REF-07, E2E-REF-11, E2E-REF-12, E2E-REF-13. **E2E-REF-09/E2E-REF-10 (generación y colisión de código de referido propio) no aplican**: esa lógica no está implementada en `handler.py` (ver Observaciones).

---

### HU-AUTH-03 — Pantalla de "verificación pendiente" tras registro
**Como** persona recién registrada **quiero** ver una confirmación clara de que mi cuenta fue creada **para** saber qué sigue.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado un registro exitoso, cuando la respuesta del backend no trae `requiresEmailVerification`, entonces el frontend **asume `true` por defecto** (`real-api.service.ts:158,167`) y siempre muestra la pantalla "Solo falta un paso, confirma tu cuenta desde tu correo electrónico" con el correo registrado (`landing.component.html:429-457`; `landing.component.ts:296-306`).
- Dado que se muestra la pantalla de verificación pendiente, cuando hay un patrocinador real asociado, entonces se ofrece un enlace de WhatsApp al patrocinador para dudas (`landing.component.html:446-449`).
- Dado que el usuario quiere corregir el correo, cuando pulsa "Usar otro correo", entonces vuelve al formulario de registro vacío (`landing.component.html:450-455`).
- El texto de la pantalla afirma que se envió "un enlace de activación" al correo; en la práctica el backend solo envía un correo de bienvenida genérico que indica "Ya puedes iniciar sesión", **sin ningún enlace ni token de activación** (`handler.py:1032-1048`; ver Observaciones).
- Dado el flujo alterno (si el backend alguna vez responde `customer` sin `requiresEmailVerification`), cuando se recibe esa respuesta, entonces la sesión se inicia automáticamente (`setUserFromCreateAccount`) y se navega a `/dashboard` sin pasar por la pantalla de verificación (`landing.component.ts:307-314`). Con el backend actual esta rama es inalcanzable porque `_create_account` nunca incluye `requiresEmailVerification: false`.

**Fuente (código):** `landing.component.ts:296-324`; `landing.component.html:429-457`; `real-api.service.ts:139-174`; `handler.py:1032-1048, 4117-4125`
**Cobertura E2E:** SIN COBERTURA EN MATRIZ (no hay un ID dedicado a validar el contenido/comportamiento de esta pantalla intermedia).

---

### HU-AUTH-04 — Verificación de email vía enlace (`/verificar-email`)
**Como** persona recién registrada **quiero** confirmar mi correo mediante el enlace recibido **para** activar mi cuenta.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que se abre `/#/verificar-email?token=...` o `/#/verify-email?token=...` (ambas rutas usan el mismo componente), cuando hay un `token` en la query, entonces el estado inicial es `loading` y se llama `POST /auth/verify-email` con `{ token }` (`app.routes.ts:31-38`; `verify-email.component.ts:25-32`).
- Dado que no hay `token` en la URL, cuando la página carga, entonces el estado pasa directo a `no-token` sin llamar al backend (`verify-email.component.ts:27-30`).
- Dado que `POST /auth/verify-email` responde 404 con mensaje "ruta no encontrada" (case-insensitive), cuando eso ocurre, entonces el frontend reintenta automáticamente contra `POST /verify-email` (sin prefijo `/auth`) como *fallback* (`real-api.service.ts:176-186`).
- Dado que la verificación es exitosa, cuando responde el backend, entonces el estado pasa a `success` y se muestra el mensaje correspondiente en la plantilla.
- Dado que la verificación falla (token inválido/expirado/usado), cuando responde el backend, entonces el estado pasa a `error` mostrando `err.error.message` o, si no viene, "El enlace es inválido o ya expiró." (`verify-email.component.ts:38-41`).
- **Ninguna de las dos rutas (`/auth/verify-email` ni `/verify-email`) está implementada en el router de `handler.py`** (no existe ningún `route_key` con primer segmento `"auth"` ni `"verify-email"`); en la práctica toda solicitud de verificación recibe `{"message": "Ruta no encontrada", "Error": "NotFound"}` con HTTP 404, y el estado final observable es siempre `error` (ver Observaciones).

**Fuente (código):** `verify-email.component.ts:1-44`; `real-api.service.ts:176-187`; `app.routes.ts:31-38`; ausencia verificada en `handler.py:6437-6515` (tabla de rutas completa).
**Cobertura E2E:** E2E-AUTH-14, E2E-AUTH-15, E2E-AUTH-16 (los tres casos están **diseñados** en la matriz pero, contra el backend real, ninguno puede completarse en estado `success` — ver Observaciones).

---

### HU-AUTH-05 — Login con redirección por rol
**Como** usuario registrado **quiero** iniciar sesión con mi correo y contraseña **para** acceder al panel que corresponde a mi rol.
**Prioridad:** Crítica
**Criterios de aceptación:**
- Dado credenciales válidas de un cliente, cuando se envía el formulario de `/login`, entonces se llama `POST /auth/login` con `{username, password}` y, al recibir `{token, user}`, se navega a `authService.defaultRoute(user)` → `/dashboard` si el usuario no tiene acceso admin (`login.component.ts:61-80, 73-79`; `auth.service.ts:150-155`).
- Dado credenciales válidas de un usuario con `canAccessAdmin=true` o `role==='admin'`, cuando se inicia sesión, entonces se navega a `/admin` (`auth.service.ts:129-155`).
- El backend soporta 3 rutas de autenticación en un mismo `POST /login` (sin prefijo `/auth`, ver Observaciones): usuarios demo hardcodeados (`_LOGIN_USERS`), empleados (`entityType_ref=="employee"`) y clientes (`CUSTOMER`) (`handler.py:6352-6412`).
- Dado un login válido, cuando el backend responde, entonces **el `token` devuelto es siempre el literal `"demo-token"`**, para cualquier usuario (demo, empleado o cliente) — no es un JWT firmado ni contiene expiración (`handler.py:6355, 6388, 6412`). La sesión se valida en el cliente únicamente comprobando que `token` sea un string no vacío (`auth.service.ts:193-195`).
- Dado un cliente identificado como "super usuario" (`_is_super_user_record`), cuando inicia sesión, entonces se le otorgan **todos** los privilegios (`_ALL_PRIVILEGES`) y `canAccessAdmin=true` sin importar lo configurado en `CUSTOMER.privileges` (`handler.py:6398-6401`).
- Dado un usuario sin `AUTH` previo pero con `CUSTOMER.passwordHash` coincidente, cuando inicia sesión, entonces el backend crea el registro `AUTH` "al vuelo" (auto-reparación de datos legados) (`handler.py:6361-6366`).

**Fuente (código):** `login.component.ts:61-87`; `auth.service.ts:52-54, 150-155`; `handler.py:6342-6412`
**Cobertura E2E:** E2E-AUTH-01, E2E-AUTH-02.

---

### HU-AUTH-06 — Validaciones y errores en el formulario de login
**Como** usuario que intenta iniciar sesión **quiero** recibir retroalimentación clara ante datos incompletos o incorrectos **para** corregir mi intento.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que el correo o la contraseña están vacíos, cuando se pulsa "Entrar", entonces se muestra "Ingresa tu correo electrónico y contraseña." y no se llama al backend (`login.component.ts:61-67`).
- Dado credenciales incorrectas, cuando el backend responde, entonces siempre es **HTTP 401** con `{"message": "Credenciales invalidas", "Error": "Unauthorized"}` (única ruta de auth que usa código de error real en lugar de 200+Error) (`handler.py:6347-6369`), y el frontend muestra ese mensaje o el genérico "Credenciales invalidas. Verifica tu correo electrónico y contraseña." (`login.component.ts:81-85`).
- Dado que se pulsa el ícono de "ojo" del campo contraseña, cuando se hace clic, entonces alterna entre texto plano y oculto (`login.component.ts:89-91`).
- Los mensajes de error de campo (`usernameError`, `passwordError`) solo aparecen **después** de un intento fallido de envío (dependen de `this.errorMessage` ya seteado), no en tiempo real mientras se escribe (`login.component.ts:41-53`).

**Fuente (código):** `login.component.ts:41-91`; `handler.py:6342-6369`
**Cobertura E2E:** E2E-AUTH-03, E2E-AUTH-06, E2E-AUTH-07.

---

### HU-AUTH-07 — Bloqueo por email no verificado y reenvío de confirmación
**Como** usuario que aún no confirmó su correo **quiero** recibir un mensaje claro y poder reenviar el correo de confirmación **para** poder activarme.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que el backend retornara el mensaje exacto `"Confirma tu cuenta desde tu correo electrónico para iniciar sesion."`, cuando el login falla con ese mensaje, entonces el frontend muestra automáticamente el botón "Reenviar correo de confirmación" (`shouldShowResendConfirmation`, comparación exacta de string) (`login.component.ts:21, 37-39`).
- Dado que se pulsa "Reenviar", cuando el campo de usuario/correo está vacío, entonces se exige "Ingresa tu correo electrónico para reenviar la confirmacion." sin llamar al backend (`login.component.ts:135-141`).
- Dado un correo válido, cuando se solicita el reenvío, entonces se llama `POST /auth/resend-email-confirmation` (`real-api.service.ts:189-200`).
- **El backend (`handler.py`) nunca emite el mensaje de bloqueo esperado**: `_login` no verifica ningún campo de tipo `emailVerified` y no existe la cadena `"Confirma tu cuenta"` en ningún punto del archivo; tampoco existe la ruta `POST /auth/resend-email-confirmation` en el router. En consecuencia, contra este backend un usuario **nunca** ve este bloqueo ni el botón de reenvío: si sus credenciales son correctas, el login siempre tiene éxito independientemente del estado de verificación de su correo (ver Observaciones).

**Fuente (código):** `login.component.ts:21, 37-39, 135-163`; `real-api.service.ts:189-200`; ausencia verificada en `handler.py` (sin coincidencias para `"Confirma tu cuenta"`, `emailVerified`, `resend-email-confirmation`).
**Cobertura E2E:** E2E-AUTH-04, E2E-AUTH-05 (diseñados en la matriz, pero no reproducibles contra el backend actual).

---

### HU-AUTH-08 — Solicitud de recuperación de contraseña (OTP)
**Como** usuario que olvidó su contraseña **quiero** solicitar un código OTP a mi correo **para** poder restablecerla.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que se pulsa "¿Olvidaste tu contraseña?" en `/login`, cuando se activa, entonces se muestra un formulario secundario con solo el campo de correo (`login.component.ts:93-104`).
- Dado que el correo está vacío, cuando se envía, entonces se exige "Ingresa tu correo electrónico para recuperar la contraseña." sin llamar al backend (`login.component.ts:106-111`).
- Dado un correo con cuenta asociada (con `AUTH` o `CUSTOMER`), cuando se solicita la recuperación, entonces el backend genera un OTP de 6 dígitos, lo guarda hasheado (SHA-256) con expiración a `PASSWORD_RESET_OTP_TTL_MINUTES` (15 min por defecto) y lo envía por correo (`handler.py:1146-1181, 200-204, 1126-1144`).
- Dado un correo **sin** cuenta asociada, cuando se solicita la recuperación, entonces el backend responde igualmente `200 {"ok": true, "message": "Si el correo existe, te enviamos un codigo OTP..."}` **sin enviar ningún correo**, evitando revelar si el correo existe (`handler.py:1164-1168`).
- Dado que el envío del correo OTP falla (SES), cuando eso ocurre para un correo que sí existe, entonces el backend responde `{"message": "No se pudo enviar el correo OTP", "Error": "EmailSendFailed"}` con HTTP 200 (`handler.py:1172-1176`) — el frontend lo interpreta como error porque revisa el campo `ok` en la respuesta (`real-api.service.ts:202-216`).
- El correo enviado incluye un enlace directo `{FRONTEND_BASE_URL}/#/recuperar-contrasena?email=...&otp=...` que precarga el formulario de reset (`handler.py:979-983`).
- Esta llamada también depende del prefijo `/auth/password/recovery`, inexistente en el router de `handler.py` (ver Observaciones): el endpoint real disponible es `POST /password/recovery` (sin `/auth`).

**Fuente (código):** `login.component.ts:93-133`; `handler.py:979-983, 1126-1181`; `real-api.service.ts:202-216`
**Cobertura E2E:** E2E-AUTH-08, E2E-AUTH-09.

---

### HU-AUTH-09 — Restablecer contraseña con OTP
**Como** usuario que solicitó recuperación **quiero** definir una nueva contraseña usando el código OTP **para** recuperar el acceso a mi cuenta.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado que se abre `/#/recuperar-contrasena?email=...&otp=...` desde el enlace del correo, cuando la página carga, entonces los campos `email` y `otp` se precargan desde la query string (`reset-password.component.ts:38-41`).
- Dado que falta correo, OTP, contraseña o confirmación, cuando se envía el formulario, entonces se exige "Completa correo, codigo, nueva contraseña y confirmacion." sin llamar al backend (`reset-password.component.ts:43-48`).
- Dado un OTP correcto y vigente, cuando se envía `email+otp+password+confirmPassword`, entonces el backend actualiza `passwordHash` tanto en `AUTH` como en `CUSTOMER`, marca el registro `PASSWORD_RESET` como `used=true` y responde `{"ok": true, "message": "Contrasena actualizada correctamente"}` (`handler.py:1183, 1215-1239`).
- Dado un OTP inexistente, ya usado, expirado (`expiresAt <= now`) o que no coincide con el hash almacenado, cuando se envía el formulario, entonces el backend responde **siempre el mismo mensaje genérico** `"OTP invalido o expirado"` con HTTP 200 + `Error: Unauthorized` (no distingue "expirado" de "incorrecto" de "ya usado" en el mensaje) (`handler.py:1194-1213`).
- Dado un intento con OTP incorrecto, cuando falla la comparación de hash, entonces el backend incrementa el contador `attempts` del registro `PASSWORD_RESET` (sin límite de intentos que bloquee el OTP) (`handler.py:1202-1213`).
- Dado que la contraseña y su confirmación no coinciden, cuando se envía, entonces el backend responde "Las contrasenas no coinciden" (validación duplicada del frontend, que no la valida localmente antes de enviar) (`handler.py:1191-1192`).
- Dado un restablecimiento exitoso, cuando el frontend recibe la respuesta, entonces muestra el mensaje de éxito y navega automáticamente a `/login` 1.2 segundos después (`reset-password.component.ts:63-69`).
- Igual que otros endpoints de auth, esta llamada depende de `POST /auth/password/reset`, no implementado con ese prefijo en `handler.py` (ruta real: `POST /password/reset`) (ver Observaciones).

**Fuente (código):** `reset-password.component.ts:1-88`; `handler.py:1183-1239`
**Cobertura E2E:** E2E-AUTH-10, E2E-AUTH-11, E2E-AUTH-12, E2E-AUTH-13 (nótese que AUTH-11 y AUTH-12 en la práctica producen el mismo mensaje genérico, no uno diferenciado como sugiere su descripción en la matriz).

---

### HU-AUTH-10 — Cambio de contraseña autenticado desde el perfil
**Como** usuario con sesión activa **quiero** cambiar mi contraseña desde mi perfil **para** mantener mi cuenta segura.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado el formulario de cambio de contraseña en `/perfil`, cuando se envía sin contraseña actual, entonces se exige "Ingresa tu contraseña actual." (`user-profile.component.ts:271-273`).
- Dado que la nueva contraseña tiene menos de 8 caracteres o está vacía, cuando se envía, entonces se exige "La nueva contraseña debe tener al menos 8 caracteres." (`user-profile.component.ts:274-276`).
- Dado que la confirmación está vacía o no coincide con la nueva contraseña, cuando se envía, entonces se exige "Confirma la nueva contraseña." o "Las contraseñas no coinciden." respectivamente (`user-profile.component.ts:277-281`).
- Dado que todas las validaciones de cliente pasan, cuando se envía, entonces se llama `POST /auth/changepassword` con `{currentPassword, newPassword}` (`user-profile.component.ts:287-290`; `real-api.service.ts:1077-1084`).
- Dado una respuesta exitosa, cuando se recibe, entonces se limpia el formulario, se ocultan los togglers de visibilidad y se muestra un toast "Contraseña actualizada correctamente." (`user-profile.component.ts:291-298`).
- **`POST /auth/changepassword` no existe en el router de `handler.py`** (ni con prefijo `/auth` ni sin él: no hay ninguna función de cambio de contraseña autenticada en todo el archivo). Toda solicitud recibe `404 {"message": "Ruta no encontrada", "Error": "NotFound"}` y el usuario ve el toast genérico "No se pudo actualizar la contraseña." (`user-profile.component.ts:299-302`; ver Observaciones).

**Fuente (código):** `user-profile.component.ts:53-58, 269-304`; `real-api.service.ts:1077-1084`; ausencia verificada en `handler.py:6437-6515`.
**Cobertura E2E:** E2E-AUTH-17, E2E-AUTH-18, E2E-AUTH-19 (diseñados, pero la ruta que consumen no está implementada).

---

### HU-AUTH-11 — Control de acceso por rol (guards)
**Como** operador de la plataforma **quiero** que cada ruta protegida valide el rol correcto **para** evitar accesos indebidos.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado un usuario sin sesión, cuando navega a `/admin`, entonces `adminGuard` redirige a `/login` (`auth.guard.ts:19-25`).
- Dado un usuario con sesión pero sin `canAccessAdmin`/`role==='admin'`/super usuario, cuando navega a `/admin`, entonces `adminGuard` lo redirige a su ruta por defecto (`/dashboard`) en vez de mostrar un error (`auth.guard.ts:19-32`; `auth.service.ts:129-137, 150-155`).
- Dado un usuario **con** acceso admin pero **sin** acceso a dashboard de cliente (`hasUserDashboardAccess=false`), cuando navega a `/dashboard` o `/perfil`, entonces `dashboardGuard` lo redirige a `/admin` (`auth.guard.ts:34-47`).
- Dado un usuario **sin sesión** (invitado), cuando navega a `/dashboard` o `/perfil`, entonces `dashboardGuard` **permite el acceso** (`if (!auth.currentUser) return true;`) — no hay bloqueo a nivel de ruta para invitados (`auth.guard.ts:38-40`).
- Para `/perfil` específicamente, el bloqueo real a usuarios sin sesión ocurre a **nivel de componente**, no de guard: `UserProfileComponent.ngOnInit` redirige a `/dashboard` si `authService.currentUser?.userId` no existe (`user-profile.component.ts:64-69`).
- `loginGuard` existe y evitaría que un usuario ya autenticado vuelva a ver el formulario de `/login`, pero **está deshabilitado**: la línea `canActivate: [loginGuard]` de la ruta `/login` está comentada (`app.routes.ts:23-26`). Un usuario con sesión activa puede navegar libremente a `/login` y ver el formulario sin ser redirigido.

**Fuente (código):** `gamificacion-multinivel-f/src/app/guards/auth.guard.ts:1-48`; `app.routes.ts:22-26, 53-57`; `user-profile.component.ts:64-69`
**Cobertura E2E:** E2E-AUTH-20, E2E-AUTH-21. No hay caso dedicado al `loginGuard` deshabilitado.

---

### HU-AUTH-12 — Persistencia de sesión y cierre de sesión (logout)
**Como** usuario autenticado **quiero** que mi sesión persista al recargar la app y poder cerrarla explícitamente **para** controlar mi acceso.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado un login exitoso, cuando se recibe el usuario, entonces se serializa a JSON y se guarda en `localStorage['auth-user']`, y se emite por el `BehaviorSubject` `user$` (`auth.service.ts:108-117`).
- Dado que se recarga la aplicación, cuando `AuthService` se inicializa, entonces intenta leer y parsear `localStorage['auth-user']`; si el JSON es inválido, limpia la clave y trata al usuario como no autenticado (`auth.service.ts:174-191`).
- Una sesión se considera "válida" (`hasSession`) únicamente si `token` es un string no vacío — no hay verificación de expiración ni de vigencia contra el backend (`auth.service.ts:48-50, 193-195`).
- Dado que el usuario pulsa "Cerrar sesión" en el dashboard, cuando se ejecuta, entonces se resetea el estado del panel, se limpia `auth-user` de `localStorage` y se navega a `/login`; **no se invoca ningún endpoint del backend** (no hay invalidación de sesión server-side, coherente con que no existe una tabla `SESSION` real ni JWT firmado) (`user-dashboard.component.ts:1142-1146`; `auth.service.ts:91-94`).

**Fuente (código):** `auth.service.ts:33-50, 91-117, 174-195`; `user-dashboard.component.ts:1142-1146`
**Cobertura E2E:** E2E-AUTH-22 (persistencia). No hay ID dedicado al logout explícito.

---

### HU-AUTH-13 — Edición de datos personales del perfil
**Como** usuario autenticado **quiero** editar mis datos personales **para** mantenerlos actualizados.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que se abre `/perfil`, cuando carga, entonces se obtiene el perfil vía `GET /customers/{userId}` y se separa el campo `name` en nombre/apellido paterno/apellido materno usando una heurística por cantidad de palabras (1, 2, 3 o más palabras) (`user-profile.component.ts:64-91, 319-330`; `handler.py:4127-4141`).
- Dado que se editan nombre, apellidos, teléfono, RFC o CURP y se guarda, entonces se envía `PATCH /customers/profile` con el nombre reconstruido y RFC/CURP en mayúsculas (`user-profile.component.ts:123-140`).
- Dado un guardado exitoso, cuando se recibe la respuesta, entonces se actualiza el perfil local y se muestra el toast "Información guardada correctamente."; si falla, se muestra "No se pudo guardar la información." (`user-profile.component.ts:134-139`).
- **`PATCH /customers/profile` no está implementado como tal en el router**: la única ruta `PATCH` de clientes es `(2, "customers", "PATCH")`, que interpreta el segundo segmento de la URL como un `customerId` numérico (`_update_customer(segments[1], ...)`, `handler.py:6482`). Con `segments[1] == "profile"`, `_update_customer` ejecuta `int("profile")`, lo cual **lanza una excepción no controlada** en vez de actualizar el perfil (`handler.py:4180-4184`). En la práctica, guardar los datos personales del perfil falla siempre contra este backend (ver Observaciones).

**Fuente (código):** `user-profile.component.ts:64-140, 306-330`; `real-api.service.ts:1086-1094`; `handler.py:4127-4241, 6482`
**Cobertura E2E:** E2E-PROF-01.

---

### HU-AUTH-14 — Registro y actualización de CLABE interbancaria
**Como** usuario asociado **quiero** registrar mi CLABE interbancaria **para** poder recibir el pago de mis comisiones.
**Prioridad:** Alta
**Criterios de aceptación:**
- Dado el campo de CLABE en `/perfil`, cuando se captura un valor con longitud distinta a 18 (tras remover espacios), entonces se bloquea localmente con el toast "La CLABE debe tener 18 dígitos." antes de mostrar el diálogo de confirmación (`user-profile.component.ts:142-150`).
- Dado una CLABE de 18 dígitos, cuando se confirma en el diálogo modal, entonces se llama `POST /customers/clabe` con `{customerId, clabe, bankInstitution}` (`user-profile.component.ts:157-166`; `real-api.service.ts:467-471`).
- El backend valida de forma redundante e independiente: `customerId` obligatorio, `clabe` obligatoria, y **exactamente** 18 dígitos numéricos (`clabe.isdigit()`), rechazando cualquier otro formato con `{"message": "CLABE invalida", "Error": "BadRequest"}` (`handler.py:5409-5418`).
- Dado un guardado exitoso, cuando se recibe la respuesta `{ok: true, clabeLast4}`, entonces el perfil local se actualiza y la UI muestra la CLABE enmascarada como `•••• •••• •••• {últimos 4 dígitos}` (`user-profile.component.ts:117-121, 169-183`).
- El backend almacena la CLABE duplicada en dos campos (`clabe` y `clabeInterbancaria`) sobre el mismo `CUSTOMER` (`handler.py:5425-5430`).
- Esta ruta (`POST /customers/clabe`, sin prefijo `/auth`) **sí coincide** con el router de `handler.py` y es, junto con `/login`, `/crearcuenta` y `/password/*`, de las pocas funcionalidades de este dominio efectivamente alcanzables.

**Fuente (código):** `user-profile.component.ts:47-51, 117-183`; `handler.py:5409-5431`
**Cobertura E2E:** E2E-PROF-02, E2E-PROF-03.

---

### HU-AUTH-15 — Carga de documentos propios (constancia/INE/CURP)
**Como** usuario asociado **quiero** subir mis documentos de identidad/fiscales **para** completar mi validación como afiliado.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado que se abre `/perfil`, cuando carga la configuración de negocio, entonces se listan los tipos de documento requeridos (`config.customerDocumentTypes`) o, si falla la carga, un set por defecto de 3 documentos: "Constancia de situación fiscal", "INE (frente y reverso)" y "CURP" (`user-profile.component.ts:93-110, 311-317`).
- Dado que se selecciona un archivo para un tipo de documento, cuando se pulsa subir, entonces el archivo se convierte a base64 en el cliente (`FileReader.readAsDataURL`) y se envía junto con `docType`, `docLabel`, `contentType` y `fileName` a `POST /customers/documents` (`user-profile.component.ts:194-235`).
- Dado un documento ya subido para un tipo, cuando se visualiza el perfil, entonces se muestra su fecha de carga y se permite abrir una vista previa si es PDF o imagen (`user-profile.component.ts:237-267`).
- Dado un error al leer el archivo localmente (`FileReader.onerror`), cuando ocurre, entonces se marca el estado de ese documento con "Error al leer el archivo." sin llamar al backend (`user-profile.component.ts:230-233`).
- **`POST /customers/documents` no está implementado en el router de `handler.py`** (no hay ningún `route_key` con segmento `"documents"` bajo `customers`); toda subida de documento propio falla con 404 y el usuario ve el toast "No se pudo subir el documento." (`user-profile.component.ts:224-227`; ausencia verificada en `handler.py:6437-6515`).

**Fuente (código):** `user-profile.component.ts:60-63, 93-110, 186-267, 311-317`; `real-api.service.ts:576-585`
**Cobertura E2E:** E2E-PROF-04, E2E-PROF-05.

---

### HU-AUTH-16 — Visualización de los datos del patrocinador
**Como** usuario asociado **quiero** ver quién es mi patrocinador y sus datos de contacto **para** poder comunicarme con él/ella.
**Prioridad:** Media
**Criterios de aceptación:**
- Dado un usuario con `leaderId` asignado, cuando abre su **dashboard** (`/dashboard`), entonces se muestran los datos del patrocinador (nombre, mensaje) con un botón para copiar su correo al portapapeles además del enlace `mailto:` (`user-dashboard.component.html:477-480`; `user-dashboard.component.ts:481`).
- **La página de perfil (`/perfil`) no contiene ninguna referencia al patrocinador**: `UserProfileComponent` no obtiene ni renderiza datos de `leaderId`/sponsor en ningún punto de su código o plantilla. La visualización del patrocinador vive exclusivamente en el dashboard, no en el perfil, a pesar de que el propio inventario de funcionalidades (`docs/qa/01-funcionalidades-sistema.md`, ítem 11.5) ya señala esta ambigüedad.
- La resolución de los datos del patrocinador (`GET /referrer/{id}`) asume nuevamente que el identificador es el `customerId` numérico, no un código de referido (`handler.py:1100-1106`).

**Fuente (código):** `user-dashboard.component.html:477-480`; `user-dashboard.component.ts:481`; `handler.py:1100-1106`; ausencia verificada en `user-profile.component.ts` y `user-profile.component.html`.
**Cobertura E2E:** E2E-PROF-06 (la matriz la ubica erróneamente como prueba de "perfil"; en el código real corresponde al dashboard). E2E-REF-03 (patrocinador visible tras registro) es la contraparte funcional real.

---

### HU-AUTH-17 — Aviso de privacidad en primer acceso (funcionalidad ausente)
**Como** usuario que se registra por primera vez **quiero** ver y aceptar un aviso de privacidad **para** que mis datos personales se traten conforme a la ley.
**Prioridad:** Baja
**Criterios de aceptación:**
- Dado que se completa el registro o se accede por primera vez a la plataforma, cuando se espera un aviso de privacidad (requisito de negocio), entonces **no existe ningún componente, modal, ruta ni texto de aviso de privacidad** en `src/` ni en `public/` (confirmado también por el inventario `docs/qa/01-funcionalidades-sistema.md`, sección 17).
- No hay checkbox de aceptación de términos/privacidad en el formulario de registro de `landing.component.html`, ni un campo `privacyAccepted`/similar en el payload de `POST /auth/crearcuenta` (`landing.component.ts:281-289`).

**Fuente (código):** ausencia verificada en `gamificacion-multinivel-f/src/app/**` (sin coincidencias para "privacidad"/"privacy" en componentes de registro/perfil); `docs/qa/01-funcionalidades-sistema.md` sección 17.
**Cobertura E2E:** E2E-PROF-07, E2E-NOTI-06 (ambos marcados como "Ausente" en la propia matriz).

---

### HU-AUTH-18 — Direcciones de envío del cliente (gestión fuera del perfil)
**Como** usuario asociado **quiero** guardar y reutilizar direcciones de envío **para** agilizar mis compras.
**Prioridad:** Media
**Criterios de aceptación:**
- El modelo de datos del `CUSTOMER` sí soporta **múltiples direcciones de envío**: `_create_account` y `_get_customer` normalizan y exponen `shippingAddresses`/`addresses` con una dirección por defecto (`handler.py:4100-4101, 4134-4140`).
- **La gestión de direcciones (alta, edición, selección) no está disponible en `/perfil`**: no existe código relacionado a direcciones en `user-profile.component.ts` ni en su plantilla. Toda la funcionalidad de direcciones guardadas vive en el checkout (`/carrito`): captura de dirección de entrega, selección de dirección guardada y checkbox para guardarla (`carrito.component.ts:62-89, 872`).
- Dado que un usuario quiere revisar/editar sus direcciones **fuera** del flujo de compra, cuando busca esa opción en su perfil, entonces no la encuentra: no hay entrada de menú, sección ni ruta dedicada a "Mis direcciones" independiente del carrito.

**Fuente (código):** `handler.py:4100-4101, 4134-4140`; `carrito.component.ts:62-89, 872`; ausencia verificada en `user-profile.component.ts`/`.html`.
**Cobertura E2E:** SIN COBERTURA EN MATRIZ desde la perspectiva de perfil. El caso más cercano, E2E-CART-10 ("Selección de dirección guardada"), cubre el flujo desde el checkout, no desde `/perfil`.

---

## Observaciones para QA

1. **Los documentos QA de referencia describen un backend distinto al que consume el frontend.**
   `docs/qa/01-funcionalidades-sistema.md` y `docs/qa/02-matriz-pruebas-e2e.md` citan mayormente
   `Micro-lambda-GMF/python/auth_utils.py` para el dominio de autenticación (verificación de email,
   JWT, generación de códigos de referido `{Nombre}-{Iniciales}`, tabla `REFERRAL_CODE#{code}`).
   El frontend (`RealApiService`) en realidad llama a endpoints que resuelve
   `gamificacion-multinivel-f/lambda/handler.py`, cuyo comportamiento es notablemente más simple y,
   en varios puntos, no implementa lo que el frontend espera. Se recomienda revalidar contra qué
   backend corre realmente el ambiente de pruebas/producción antes de ejecutar la matriz E2E-AUTH/E2E-REF/E2E-PROF.

2. **Desalineación de prefijo `/auth` entre frontend y backend.** `RealApiService` llama
   `/auth/login`, `/auth/crearcuenta`, `/auth/verify-email`, `/auth/resend-email-confirmation`,
   `/auth/password/recovery`, `/auth/password/reset` y `/auth/changepassword`. El router de
   `handler.py` (línea `route_key = (len(segments), segments[0], method)`, `handler.py:6437`)
   solo registra `/login`, `/crearcuenta`, `/password/recovery` y `/password/reset` **sin** el
   prefijo `/auth`, y no hay `verify-email`, `resend-email-confirmation` ni `changepassword` con
   ningún prefijo. Todo el archivo termina con un catch-all `404 "Ruta no encontrada"` (`handler.py:6515`).
   Solo el flujo de verificación de email tiene un *fallback* explícito en el frontend hacia la
   ruta sin prefijo (`real-api.service.ts:176-186`), que tampoco existe en el backend.

3. **El "token" de sesión no es un JWT.** `_login` retorna siempre el literal `"demo-token"`
   (`handler.py:6355, 6388, 6412`) para cualquier usuario exitosamente autenticado. No hay firma,
   expiración, ni vínculo criptográfico entre el token y el usuario — la identidad viaja en el
   campo `user` de la respuesta, no en el token. El frontend valida la sesión solo comprobando que
   `token` sea un string no vacío (`auth.service.ts:193-195`).

4. **No existe verificación de correo real en el backend consumido.** No hay generación de token
   de verificación, no hay endpoint de verificación alcanzable y no hay campo `emailVerified` en
   ningún punto de `handler.py`. El correo que sí se envía al registrarse (`_send_welcome_email`)
   afirma explícitamente "Ya puedes iniciar sesión" (`handler.py:1037`), contradiciendo la pantalla
   del frontend que le dice al usuario que debe "confirmar su cuenta" con un enlace de activación
   que nunca llega.

5. **El login nunca bloquea por correo no verificado.** El frontend tiene lista toda la UX para el
   mensaje "Confirma tu cuenta..." (`login.component.ts:21`), pero como el backend no implementa
   ese chequeo, cualquier cuenta con credenciales correctas puede iniciar sesión de inmediato.

6. **La generación de código de referido propio no está implementada.** El "referral token" real es
   el `customerId` numérico crudo (`_resolve_leader_id`, `handler.py:395-400`); no hay generación de
   códigos tipo `{Nombre}-{Iniciales}` ni tabla de resolución de códigos. Los IDs E2E-REF-09/E2E-REF-10
   de la matriz no son ejecutables contra este backend.

7. **Código de referido/patrocinador inexistente falla en silencio.** Si el token de referido
   (numérico) no corresponde a ningún cliente, el registro **continúa sin error**, simplemente sin
   patrocinador asignado (`handler.py:395-400, 4083`). El mensaje de error esperado por E2E-REF-06
   no existe.

8. **Varios endpoints de perfil no están implementados y producen fallas silenciosas o excepciones:**
   `PATCH /customers/profile` (los datos personales) cae en `_update_customer("profile", ...)` y
   provoca una excepción al intentar `int("profile")` (`handler.py:4180-4184, 6482`);
   `POST /auth/changepassword` y `POST /customers/documents` simplemente no existen en el router.
   Los tres casos degradan a un toast de error genérico en el frontend, sin indicar la causa real.

9. **`loginGuard` está deshabilitado.** La ruta `/login` tiene el guard comentado
   (`app.routes.ts:23-26`), por lo que un usuario ya autenticado puede volver a ver el formulario de
   login sin ser redirigido a su panel.

10. **No existe la ruta `/reset-password`.** Solo está registrada `/recuperar-contrasena` (con alias
    de componente compartido con ninguna otra ruta) en `app.routes.ts:27-30`. Cualquier prueba o
    enlace que asuma `/reset-password` como ruta del frontend fallará.

11. **Convención de errores inconsistente.** La mayoría de los endpoints de este dominio (crear
    cuenta, recuperar/reset de contraseña, CLABE) devuelven **HTTP 200** con un cuerpo
    `{"message": ..., "Error": "..."}` para señalar fallas de negocio, en vez de códigos 4xx. La
    única excepción es `/login`, que sí usa 401 para credenciales inválidas. Los criterios de
    aceptación y aserciones de prueba deben validar el cuerpo de la respuesta, no solo el código HTTP.

12. **`/perfil` no gestiona ni el patrocinador ni las direcciones de envío**, pese a ser un lugar
    intuitivo para ambas cosas: el patrocinador se muestra solo en `/dashboard` y las direcciones
    solo se gestionan dentro del checkout (`/carrito`).
