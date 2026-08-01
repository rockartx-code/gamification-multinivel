import { test, expect, seedSession, acceptPrivacyNotice, USERS, mockApi, blockUnmockedApi, API_BASE } from './support/fixtures';

// Dominio: Autenticación (login, recuperación/reset de contraseña, guards, sesión).
// Fuente de verdad: docs/hu/01-hu-auth-registro-perfil.md (HU-AUTH-05 a HU-AUTH-12)
//                    docs/qa/02-matriz-pruebas-e2e.md (E2E-AUTH-*)
//
// Quirks aplicados (ver docs/hu):
// - El login real usa POST /auth/login con {username, password} y devuelve {user, token}.
//   El "token" siempre es un string no vacío (nunca se valida como JWT en el cliente).
// - Las llamadas de auth SIEMPRE llevan el prefijo /auth (así las intercepta el frontend,
//   independientemente de si el backend real las implementa con ese prefijo).
// - login.component.ts NO tiene <form>; el campo de correo es un ui-form-field
//   (usar getByRole('textbox', {name: 'Correo electrónico'})); el password es un <input> crudo
//   (usar getByPlaceholder('Tu contraseña')).

test.describe('HU-AUTH-05: Login con redirección por rol', () => {
  test('HU-AUTH-05 / E2E-AUTH-01: login exitoso de cliente redirige a /dashboard', async ({ page }) => {
    await acceptPrivacyNotice(page);
    // NOTA: Playwright invoca los page.route() en orden inverso al de registro (LIFO), así que
    // blockUnmockedApi (catch-all) debe registrarse SIEMPRE antes que los mocks específicos, para
    // que estos últimos (registrados después) tengan prioridad y no queden tapados por el 500.
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/login', {
      user: { userId: 'cust-e2e-100', name: 'Cliente Login E2E', role: 'cliente', canAccessAdmin: false },
      token: 'demo-token'
    }, { method: 'POST' });

    await page.goto('/#/login');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('cliente@e2e.test');
    await page.getByPlaceholder('Tu contraseña').fill('Sup3rSecreta!');
    await page.getByRole('button', { name: 'Ingresar al panel' }).click();

    await expect(page).toHaveURL(/#\/dashboard/);
  });

  test('HU-AUTH-05 / E2E-AUTH-02: login exitoso de admin redirige a /admin', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/login', {
      user: { userId: 'admin-100', name: 'Admin Login E2E', role: 'admin', canAccessAdmin: true, isSuperUser: true },
      token: 'demo-token'
    }, { method: 'POST' });

    await page.goto('/#/login');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('admin@e2e.test');
    await page.getByPlaceholder('Tu contraseña').fill('Sup3rSecreta!');
    await page.getByRole('button', { name: 'Ingresar al panel' }).click();

    await expect(page).toHaveURL(/#\/admin/);
  });
});

test.describe('HU-AUTH-06: Validaciones y errores en el formulario de login', () => {
  test('HU-AUTH-06 / E2E-AUTH-03: credenciales inválidas muestra error y no crea sesión', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/login', { message: 'Credenciales invalidas', Error: 'Unauthorized' }, {
      method: 'POST',
      status: 401
    });

    await page.goto('/#/login');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('cliente@e2e.test');
    await page.getByPlaceholder('Tu contraseña').fill('claveMala');
    await page.getByRole('button', { name: 'Ingresar al panel' }).click();

    await expect(page.getByText('Credenciales invalidas')).toBeVisible();
    await expect(page).toHaveURL(/#\/login/);
    expect(await page.evaluate(() => localStorage.getItem('auth-user'))).toBeNull();
  });

  test('HU-AUTH-06 / E2E-AUTH-06: campos vacíos bloquea el envío sin llamar al backend', async ({ page }) => {
    await acceptPrivacyNotice(page);
    let loginCalled = false;
    await page.route(`${API_BASE}/auth/login`, (route) => {
      loginCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/login');
    await page.getByRole('button', { name: 'Ingresar al panel' }).click();

    await expect(page.getByText('Ingresa tu correo electrónico y contraseña.')).toBeVisible();
    expect(loginCalled).toBe(false);
  });

  test('HU-AUTH-06 / E2E-AUTH-07: toggle de visibilidad de contraseña alterna texto/oculto', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await page.goto('/#/login');

    const passwordInput = page.getByPlaceholder('Tu contraseña');
    await passwordInput.fill('miClaveSecreta');
    await expect(passwordInput).toHaveAttribute('type', 'password');

    await page.getByRole('button', { name: 'Mostrar contraseña' }).click();
    await expect(passwordInput).toHaveAttribute('type', 'text');

    await page.getByRole('button', { name: 'Ocultar contraseña' }).click();
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });
});

test.describe('HU-AUTH-07: Bloqueo por email no verificado y reenvío de confirmación', () => {
  // La cadena exacta esperada por login.component.ts (shouldShowResendConfirmation compara string exacto).
  const CONFIRMATION_MESSAGE = 'Confirma tu cuenta desde tu correo electrónico para iniciar sesion.';

  test('HU-AUTH-07 / E2E-AUTH-04: mensaje de confirmación pendiente muestra el botón de reenvío', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/login', { message: CONFIRMATION_MESSAGE, Error: 'Unauthorized' }, {
      method: 'POST',
      status: 401
    });

    await page.goto('/#/login');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('sinverificar@e2e.test');
    await page.getByPlaceholder('Tu contraseña').fill('Sup3rSecreta!');
    await page.getByRole('button', { name: 'Ingresar al panel' }).click();

    await expect(page.getByText(CONFIRMATION_MESSAGE)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reenviar correo de confirmacion' })).toBeVisible();
  });

  test('HU-AUTH-07 / E2E-AUTH-05: reenviar correo de confirmación muestra mensaje de éxito', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/login', { message: CONFIRMATION_MESSAGE, Error: 'Unauthorized' }, {
      method: 'POST',
      status: 401
    });
    await mockApi(page, '/auth/resend-email-confirmation', {
      ok: true,
      message: 'Te reenviamos el correo de confirmación.'
    }, { method: 'POST' });

    await page.goto('/#/login');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('sinverificar@e2e.test');
    await page.getByPlaceholder('Tu contraseña').fill('Sup3rSecreta!');
    await page.getByRole('button', { name: 'Ingresar al panel' }).click();
    await expect(page.getByRole('button', { name: 'Reenviar correo de confirmacion' })).toBeVisible();

    await page.getByRole('button', { name: 'Reenviar correo de confirmacion' }).click();
    await expect(page.getByText('Te reenviamos el correo de confirmación.')).toBeVisible();
  });

  test('HU-AUTH-07: reenviar con el campo de correo vacío exige el dato sin llamar al backend', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/login', { message: CONFIRMATION_MESSAGE, Error: 'Unauthorized' }, {
      method: 'POST',
      status: 401
    });
    let resendCalled = false;
    await page.route(`${API_BASE}/auth/resend-email-confirmation`, (route) => {
      resendCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/login');
    const usernameField = page.getByRole('textbox', { name: 'Correo electrónico' });
    await usernameField.fill('sinverificar@e2e.test');
    await page.getByPlaceholder('Tu contraseña').fill('Sup3rSecreta!');
    await page.getByRole('button', { name: 'Ingresar al panel' }).click();
    await expect(page.getByRole('button', { name: 'Reenviar correo de confirmacion' })).toBeVisible();

    // Se limpia el correo DESPUÉS de que apareció el botón, para forzar la validación local.
    await usernameField.fill('');
    await page.getByRole('button', { name: 'Reenviar correo de confirmacion' }).click();

    await expect(page.getByText('Ingresa tu correo electrónico para reenviar la confirmacion.')).toBeVisible();
    expect(resendCalled).toBe(false);
  });
});

test.describe('HU-AUTH-08: Solicitud de recuperación de contraseña (OTP)', () => {
  test('HU-AUTH-08 / E2E-AUTH-08: recuperación con correo existente responde con OTP enviado', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/password/recovery', {
      ok: true,
      message: 'Si el correo existe, te enviamos un codigo OTP a tu correo electronico.'
    }, { method: 'POST' });

    await page.goto('/#/login');
    await page.getByRole('button', { name: 'Recuperar contraseña' }).click();
    // No es un <hN>: login.component.html lo renderiza como <div>, no como heading ARIA.
    await expect(page.getByText('Recupera el acceso')).toBeVisible();

    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('existe@e2e.test');
    await page.getByRole('button', { name: 'Enviar Correo de recuperación' }).click();

    await expect(page.getByText('Si el correo existe, te enviamos un codigo OTP a tu correo electronico.')).toBeVisible();
  });

  test('HU-AUTH-08 / E2E-AUTH-09: recuperación con correo inexistente responde igual (200 genérico, no revela existencia)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/password/recovery', {
      ok: true,
      message: 'Si el correo existe, te enviamos un codigo OTP a tu correo electronico.'
    }, { method: 'POST' });

    await page.goto('/#/login');
    await page.getByRole('button', { name: 'Recuperar contraseña' }).click();
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('no-existe@e2e.test');
    await page.getByRole('button', { name: 'Enviar Correo de recuperación' }).click();

    // Mismo mensaje genérico que con correo existente: el backend nunca revela si el correo existe.
    await expect(page.getByText('Si el correo existe, te enviamos un codigo OTP a tu correo electronico.')).toBeVisible();
  });

  test('HU-AUTH-08: solicitar recuperación sin correo exige el dato sin llamar al backend', async ({ page }) => {
    await acceptPrivacyNotice(page);
    let recoveryCalled = false;
    await page.route(`${API_BASE}/auth/password/recovery`, (route) => {
      recoveryCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/login');
    await page.getByRole('button', { name: 'Recuperar contraseña' }).click();
    await page.getByRole('button', { name: 'Enviar Correo de recuperación' }).click();

    await expect(page.getByText('Ingresa tu correo electrónico para recuperar la contraseña.')).toBeVisible();
    expect(recoveryCalled).toBe(false);
  });
});

test.describe('HU-AUTH-09: Restablecer contraseña con OTP', () => {
  test('HU-AUTH-09 / E2E-AUTH-10: reset con OTP válido actualiza la contraseña y redirige a login', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/password/reset', { ok: true, message: 'Contrasena actualizada correctamente' }, {
      method: 'POST'
    });

    await page.goto('/#/recuperar-contrasena');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('reset@e2e.test');
    await page.getByRole('textbox', { name: 'OTP' }).fill('123456');
    await page.getByPlaceholder('Nueva contraseña').fill('NuevaClave123!');
    await page.getByPlaceholder('Repite la contraseña').fill('NuevaClave123!');
    await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click();

    await expect(page.getByText('Contrasena actualizada correctamente')).toBeVisible();
    // reset-password.component.ts navega a /login 1.2s después del éxito.
    await expect(page).toHaveURL(/#\/login/, { timeout: 5000 });
  });

  test('HU-AUTH-09 / E2E-AUTH-11: reset con OTP expirado muestra el error genérico del backend', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/password/reset', { message: 'OTP invalido o expirado', Error: 'Unauthorized' }, {
      method: 'POST'
    });

    await page.goto('/#/recuperar-contrasena');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('reset@e2e.test');
    await page.getByRole('textbox', { name: 'OTP' }).fill('000000');
    await page.getByPlaceholder('Nueva contraseña').fill('NuevaClave123!');
    await page.getByPlaceholder('Repite la contraseña').fill('NuevaClave123!');
    await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click();

    await expect(page.getByText('OTP invalido o expirado')).toBeVisible();
    await expect(page).toHaveURL(/#\/recuperar-contrasena/);
  });

  test('HU-AUTH-09 / E2E-AUTH-12: reset con OTP ya usado muestra el mismo mensaje genérico (no distingue el motivo)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    // handler.py nunca distingue "expirado" de "ya usado" en el mensaje: mismo texto que AUTH-11.
    await mockApi(page, '/auth/password/reset', { message: 'OTP invalido o expirado', Error: 'Unauthorized' }, {
      method: 'POST'
    });

    await page.goto('/#/recuperar-contrasena');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('reset@e2e.test');
    await page.getByRole('textbox', { name: 'OTP' }).fill('111111');
    await page.getByPlaceholder('Nueva contraseña').fill('NuevaClave123!');
    await page.getByPlaceholder('Repite la contraseña').fill('NuevaClave123!');
    await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click();

    await expect(page.getByText('OTP invalido o expirado')).toBeVisible();
  });

  test('HU-AUTH-09 / E2E-AUTH-13: reset con contraseñas que no coinciden muestra el error del backend', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/password/reset', { message: 'Las contrasenas no coinciden', Error: 'BadRequest' }, {
      method: 'POST'
    });

    await page.goto('/#/recuperar-contrasena');
    await page.getByRole('textbox', { name: 'Correo electrónico' }).fill('reset@e2e.test');
    await page.getByRole('textbox', { name: 'OTP' }).fill('123456');
    await page.getByPlaceholder('Nueva contraseña').fill('ClaveUno123!');
    await page.getByPlaceholder('Repite la contraseña').fill('ClaveDistinta456!');
    await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click();

    await expect(page.getByText('Las contrasenas no coinciden')).toBeVisible();
  });

  test('HU-AUTH-09: reset con campos vacíos bloquea el envío localmente', async ({ page }) => {
    await acceptPrivacyNotice(page);
    let resetCalled = false;
    await page.route(`${API_BASE}/auth/password/reset`, (route) => {
      resetCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/recuperar-contrasena');
    await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click();

    await expect(page.getByText('Completa correo, codigo, nueva contraseña y confirmacion.')).toBeVisible();
    expect(resetCalled).toBe(false);
  });
});

test.describe('HU-AUTH-11: Control de acceso por rol (guards)', () => {
  test('HU-AUTH-11 / E2E-AUTH-20: acceso a /admin sin sesión redirige a /login', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);

    await page.goto('/#/admin');

    await expect(page).toHaveURL(/#\/login/);
  });

  test('HU-AUTH-11 / E2E-AUTH-20: acceso a /admin con sesión de cliente (sin rol admin) redirige a /dashboard', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);

    await page.goto('/#/admin');

    await expect(page).toHaveURL(/#\/dashboard/);
    await expect(page).not.toHaveURL(/#\/admin$/);
  });

  test('HU-AUTH-11 / E2E-AUTH-21: acceso a /dashboard sin sesión está permitido (invitado, sin bloqueo de ruta)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);

    await page.goto('/#/dashboard');

    await expect(page).not.toHaveURL(/#\/login/);
    await expect(page).toHaveURL(/#\/dashboard/);
  });

  test('HU-AUTH-11 / E2E-AUTH-21: acceso a /perfil sin sesión redirige a /dashboard (bloqueo a nivel de componente)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);

    await page.goto('/#/perfil');

    // dashboardGuard permite el acceso (invitado), pero UserProfileComponent.ngOnInit
    // redirige manualmente si no hay authService.currentUser?.userId.
    await expect(page).toHaveURL(/#\/dashboard/);
  });

  test('HU-AUTH-11: loginGuard está deshabilitado — con sesión activa, /login sigue siendo accesible', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);

    await page.goto('/#/login');

    // app.routes.ts tiene `canActivate: [loginGuard]` comentado: no hay redirección.
    await expect(page).toHaveURL(/#\/login/);
    await expect(page.getByRole('textbox', { name: 'Correo electrónico' })).toBeVisible();
  });
});

test.describe('HU-AUTH-12: Persistencia de sesión y cierre de sesión (logout)', () => {
  test('HU-AUTH-12 / E2E-AUTH-22: la sesión persiste tras recargar la aplicación', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);

    await page.goto('/#/dashboard');
    await expect(page).not.toHaveURL(/#\/login/);

    await page.reload();

    await expect(page).not.toHaveURL(/#\/login/);
    expect(await page.evaluate(() => localStorage.getItem('auth-user'))).not.toBeNull();
  });

  test('HU-AUTH-12: cerrar sesión limpia el localStorage y navega a /login', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, '/customers/dashboard', {
      isGuest: false,
      settings: { cutoffDay: 25, cutoffHour: 23, cutoffMinute: 59, userCode: 'ABC123', networkGoal: 300 },
      goals: [],
      networkMembers: [],
      buyAgainIds: [],
      commissions: null,
      notifications: []
    }, { method: 'GET' });
    await mockApi(page, '/catalog/catalog', { products: [], productOfMonth: null }, { method: 'GET' });

    await page.goto('/#/dashboard');
    // El aria-label="Usuario" vive en el host <ui-button>, no en el <button> nativo interno, así
    // que no forma parte de su nombre accesible real (que termina siendo el texto visible, p. ej.
    // "30% Cliente E2E"); se hace click sobre el contenedor #user-circle en su lugar.
    await page.locator('#user-circle').click();
    await page.getByRole('button', { name: 'Cerrar sesion' }).click();

    await expect(page).toHaveURL(/#\/login/);
    expect(await page.evaluate(() => localStorage.getItem('auth-user'))).toBeNull();
  });
});

// NO AUTOMATIZADAS:
// - Nada del dominio de autenticación quedó fuera por completo en este archivo; los casos que la
//   matriz asocia a AUTH pero dependen de datos cruzados con otros dominios (p. ej. abrir la red
//   del patrocinador para validar comisiones) se cubren, si aplica, en registro-perfil.spec.ts o
//   quedan fuera de alcance de "Autenticación, Registro y Perfil".
