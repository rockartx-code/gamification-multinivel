import { Page } from '@playwright/test';
import { test, expect, seedSession, acceptPrivacyNotice, USERS, mockApi, blockUnmockedApi, API_BASE } from './support/fixtures';

// Dominio: Registro de cuenta, vinculación con patrocinador, verificación de email y Perfil.
// Fuente de verdad: docs/hu/01-hu-auth-registro-perfil.md (HU-AUTH-01,02,03,04,10,13-18)
//                    docs/qa/02-matriz-pruebas-e2e.md (E2E-REF-*, E2E-AUTH-14/15/16/17/18/19, E2E-PROF-*)
//
// Quirks aplicados (ver docs/hu):
// - landing.component.ts NO tiene <form>. Todos los campos (incluidos los de tipo password) son
//   ui-form-field y SÍ exponen role "textbox" (Chromium expone role=textbox también para
//   input[type=password]). OJO: el nombre accesible de un campo password incluye además el texto
//   del botón de mostrar/ocultar ("Contraseña * Mostrar contraseña"), y "Confirmar contraseña *"
//   contiene "contraseña *" como substring de "Contraseña *" — por eso se usa un regex anclado al
//   inicio (`/^Contraseña \*/`) para no chocar con "Confirmar contraseña *". El atributo `name`
//   plano en <ui-form-field name="password"> NO llega al <input> real (UiFormFieldComponent no lo
//   refleja), así que `input[name="..."]` NUNCA matchea: no usar ese selector con ui-form-field.
// - user-profile.component.html: los 3 campos de "Cambiar contraseña" son <input> crudos con una
//   etiqueta NO asociada (sin for/id) => sin nombre accesible; se usan sus placeholders.
// - POST /auth/crearcuenta, POST /auth/verify-email, POST /customers/clabe, etc. siguen el mismo
//   patrón mockeado: intercepción sobre API_BASE, nunca contra AWS real.
// - Playwright invoca los page.route() en orden inverso al de registro (LIFO): blockUnmockedApi
//   (catch-all) se registra SIEMPRE primero, y los mocks específicos (mockApi/page.route puntuales)
//   se registran después, para que tengan prioridad sobre el 500 genérico.

async function fillRegistrationForm(
  page: Page,
  data: {
    firstName?: string;
    apellidoPaterno?: string;
    apellidoMaterno?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
    referralCode?: string;
  }
): Promise<void> {
  if (data.firstName !== undefined) {
    await page.getByRole('textbox', { name: 'Nombre(s) *' }).fill(data.firstName);
  }
  if (data.apellidoPaterno !== undefined) {
    await page.getByRole('textbox', { name: 'Apellido paterno *' }).fill(data.apellidoPaterno);
  }
  if (data.apellidoMaterno !== undefined) {
    await page.getByRole('textbox', { name: 'Apellido materno *' }).fill(data.apellidoMaterno);
  }
  if (data.email !== undefined) {
    await page.getByRole('textbox', { name: 'Correo electrónico *' }).fill(data.email);
  }
  if (data.password !== undefined) {
    await page.getByRole('textbox', { name: /^Contraseña \*/ }).fill(data.password);
  }
  if (data.confirmPassword !== undefined) {
    await page.getByRole('textbox', { name: /^Confirmar contraseña \*/ }).fill(data.confirmPassword);
  }
  if (data.referralCode !== undefined) {
    await page.getByRole('textbox', { name: 'Código de Referido (opcional)' }).fill(data.referralCode);
  }
}

const VALID_REGISTRATION = {
  firstName: 'Ana',
  apellidoPaterno: 'Perez',
  apellidoMaterno: 'Lopez',
  password: 'Clave12345!',
  confirmPassword: 'Clave12345!'
};

test.describe('HU-AUTH-01: Registro de cuenta (datos básicos, validación y duplicado de correo)', () => {
  test('HU-AUTH-01 / E2E-REF-08: registro con correo ya registrado muestra el error de duplicado', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/crearcuenta', {
      message: 'El correo ya esta registrado. Intenta usar recuperar contrasena.',
      Error: 'Conflict'
    }, { method: 'POST' });

    await page.goto('/#/landing');
    await fillRegistrationForm(page, { ...VALID_REGISTRATION, email: 'ana.duplicada@e2e.test' });
    await page.getByRole('button', { name: 'Unirme ahora' }).click();

    await expect(page.getByText('El correo ya esta registrado. Intenta usar recuperar contrasena.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Crea tu cuenta gratis' })).toBeVisible();
  });

  test('HU-AUTH-01: campos obligatorios vacíos se marcan en rojo sin llamar al backend', async ({ page }) => {
    await acceptPrivacyNotice(page);
    let createAccountCalled = false;
    await page.route(`${API_BASE}/auth/crearcuenta`, (route) => {
      createAccountCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/landing');
    await page.getByRole('button', { name: 'Unirme ahora' }).click();

    await expect(page.getByText('El nombre es obligatorio.')).toBeVisible();
    await expect(page.getByText('El apellido paterno es obligatorio.')).toBeVisible();
    await expect(page.getByText('El apellido materno es obligatorio.')).toBeVisible();
    await expect(page.getByText('El correo electrónico es obligatorio.')).toBeVisible();
    await expect(page.getByText('La contraseña es obligatoria.')).toBeVisible();
    expect(createAccountCalled).toBe(false);
  });

  test('HU-AUTH-01: contraseñas que no coinciden bloquea el envío del registro', async ({ page }) => {
    await acceptPrivacyNotice(page);
    let createAccountCalled = false;
    await page.route(`${API_BASE}/auth/crearcuenta`, (route) => {
      createAccountCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/landing');
    await fillRegistrationForm(page, {
      firstName: 'Ana',
      apellidoPaterno: 'Perez',
      apellidoMaterno: 'Lopez',
      email: 'ana@e2e.test',
      password: 'ClaveUno123!',
      confirmPassword: 'ClaveDistinta456!'
    });
    await page.getByRole('button', { name: 'Unirme ahora' }).click();

    await expect(page.getByText('Las contraseñas no coinciden.')).toBeVisible();
    expect(createAccountCalled).toBe(false);
  });
});

test.describe('HU-AUTH-02: Vinculación con patrocinador al registrarse', () => {
  test('HU-AUTH-02 / E2E-REF-01: registro vía /landing/:idSponsor envía el referralToken del patrocinador', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/customers/sponsor/12345', {
      sponsor: { name: 'Jorge Referidor', email: 'jorge@e2e.test', phone: '5215555555555', isDefault: false }
    }, { method: 'GET' });
    await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 999001, requiresEmailVerification: true }, {
      method: 'POST'
    });

    await page.goto('/#/landing/12345');
    await expect(page.getByText('Jorge Referidor')).toBeVisible();
    // Con referralToken en la ruta, el campo manual de código de referido no se muestra.
    await expect(page.getByRole('textbox', { name: 'Código de Referido (opcional)' })).toHaveCount(0);

    await fillRegistrationForm(page, { ...VALID_REGISTRATION, email: 'nuevo.con.sponsor@e2e.test' });
    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url() === `${API_BASE}/auth/crearcuenta` && req.method() === 'POST'),
      page.getByRole('button', { name: 'Unirme ahora' }).click()
    ]);

    expect(request.postDataJSON().referralToken).toBe('12345');
    await expect(page.getByRole('heading', { name: 'Solo falta un paso, confirma tu cuenta desde tu correo electrónico' })).toBeVisible();
  });

  test('HU-AUTH-02 / E2E-REF-13: el leaderId de la landing persiste en localStorage tras visitar la ruta con patrocinador', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/customers/sponsor/54321', { sponsor: { name: 'X', email: 'x@e2e.test', phone: '1', isDefault: false } }, {
      method: 'GET'
    });

    await page.goto('/#/landing/54321');

    expect(await page.evaluate(() => localStorage.getItem('leaderId'))).toBe('54321');
  });

  test('HU-AUTH-02 / E2E-REF-07: registro directo sin patrocinador (código manual disponible, cuenta creada sin leaderId)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 999002, requiresEmailVerification: true }, {
      method: 'POST'
    });

    await page.goto('/#/landing');
    await expect(page.getByRole('textbox', { name: 'Código de Referido (opcional)' })).toBeVisible();

    await fillRegistrationForm(page, { ...VALID_REGISTRATION, email: 'directo@e2e.test' });
    const [request] = await Promise.all([
      page.waitForRequest((req) => req.url() === `${API_BASE}/auth/crearcuenta` && req.method() === 'POST'),
      page.getByRole('button', { name: 'Unirme ahora' }).click()
    ]);

    expect(request.postDataJSON().referralToken).toBeUndefined();
    await expect(page.getByRole('heading', { name: 'Solo falta un paso, confirma tu cuenta desde tu correo electrónico' })).toBeVisible();
  });

  test('HU-AUTH-02 / E2E-REF-06: un código de referido manual inexistente no bloquea el registro (falla en silencio)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    // El backend real no valida el referralToken contra ningún catálogo: si no existe, la cuenta
    // se crea igual sin patrocinador y sin mensaje de error (handler.py: _resolve_leader_id retorna None).
    await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 999003, requiresEmailVerification: true }, {
      method: 'POST'
    });

    await page.goto('/#/landing');
    await fillRegistrationForm(page, {
      ...VALID_REGISTRATION,
      email: 'codigo.inexistente@e2e.test',
      referralCode: 'CODIGO-INEXISTENTE'
    });
    await page.getByRole('button', { name: 'Unirme ahora' }).click();

    // No hay ningún mensaje de "código inválido": el registro simplemente avanza a la pantalla pendiente.
    await expect(page.getByRole('heading', { name: 'Solo falta un paso, confirma tu cuenta desde tu correo electrónico' })).toBeVisible();
  });
});

test.describe('HU-AUTH-03: Pantalla de "verificación pendiente" tras registro', () => {
  test('HU-AUTH-03: la pantalla pendiente muestra el correo registrado y "Usar otro correo" regresa al formulario', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 999004, requiresEmailVerification: true }, {
      method: 'POST'
    });

    await page.goto('/#/landing');
    await fillRegistrationForm(page, { ...VALID_REGISTRATION, email: 'pendiente@e2e.test' });
    await page.getByRole('button', { name: 'Unirme ahora' }).click();

    await expect(page.getByText('pendiente@e2e.test')).toBeVisible();

    await page.getByRole('button', { name: 'Usar otro correo' }).click();

    await expect(page.getByRole('heading', { name: 'Crea tu cuenta gratis' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Nombre(s) *' })).toHaveValue('');
  });

  test('HU-AUTH-03 / E2E-REF-03: con patrocinador real, la pantalla pendiente ofrece el enlace de WhatsApp', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/customers/sponsor/777', {
      sponsor: { name: 'Laura Mentora', email: 'laura@e2e.test', phone: '5219998887777', isDefault: false }
    }, { method: 'GET' });
    await mockApi(page, '/auth/crearcuenta', { ok: true, customerId: 999005, requiresEmailVerification: true }, {
      method: 'POST'
    });

    await page.goto('/#/landing/777');
    await fillRegistrationForm(page, { ...VALID_REGISTRATION, email: 'con.sponsor@e2e.test' });
    await page.getByRole('button', { name: 'Unirme ahora' }).click();

    await expect(page.getByRole('link', { name: /Escríbele a Laura/ })).toBeVisible();
  });
});

test.describe('HU-AUTH-04: Verificación de email vía enlace (/verificar-email)', () => {
  test('HU-AUTH-04 / E2E-AUTH-14: verificar email con token válido muestra el estado de éxito', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/verify-email', { ok: true }, { method: 'POST' });

    await page.goto('/#/verificar-email?token=token-valido-123');

    await expect(page.getByRole('heading', { name: '¡Correo verificado!' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Iniciar sesión' })).toBeVisible();
  });

  test('HU-AUTH-04 / E2E-AUTH-15: verificar email con token inválido o expirado muestra el estado de error', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/verify-email', { message: 'El enlace es inválido o ya expiró.' }, {
      method: 'POST',
      status: 400
    });

    await page.goto('/#/verificar-email?token=token-expirado');

    await expect(page.getByRole('heading', { name: 'Enlace inválido' })).toBeVisible();
    await expect(page.getByText('El enlace es inválido o ya expiró.')).toBeVisible();
  });

  test('HU-AUTH-04 / E2E-AUTH-16: verificar email sin token en la URL muestra "no-token" sin llamar al backend', async ({ page }) => {
    await acceptPrivacyNotice(page);
    let verifyCalled = false;
    await page.route(`${API_BASE}/auth/verify-email`, (route) => {
      verifyCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });
    await page.route(`${API_BASE}/verify-email`, (route) => {
      verifyCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/verificar-email');

    await expect(page.getByRole('heading', { name: 'Verifica tu correo' })).toBeVisible();
    expect(verifyCalled).toBe(false);
  });

  test('HU-AUTH-04: si /auth/verify-email responde 404 "ruta no encontrada", reintenta contra /verify-email (fallback sin prefijo)', async ({ page }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, '/auth/verify-email', { message: 'Ruta no encontrada', Error: 'NotFound' }, {
      method: 'POST',
      status: 404
    });
    await mockApi(page, '/verify-email', { ok: true }, { method: 'POST' });

    await page.goto('/#/verify-email?token=token-fallback');

    await expect(page.getByRole('heading', { name: '¡Correo verificado!' })).toBeVisible();
  });
});

test.describe('HU-AUTH-13: Edición de datos personales del perfil', () => {
  test.beforeEach(async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, `/customers/${USERS.cliente.userId}`, {
      customer: {
        customerId: USERS.cliente.userId,
        name: 'Ana Torres Ruiz',
        email: 'ana.torres@e2e.test',
        phone: '5512345678',
        rfc: '',
        curp: '',
        clabeInterbancaria: '',
        bankInstitution: '',
        documents: [],
        ownDocuments: []
      }
    }, { method: 'GET' });
  });

  test('HU-AUTH-13 / E2E-PROF-01: editar datos personales y guardar actualiza el perfil', async ({ page }) => {
    await mockApi(page, '/customers/profile', {
      customer: { id: USERS.cliente.userId, name: 'Ana Torres Ruiz', email: 'ana.torres@e2e.test', phone: '5599998888' }
    }, { method: 'PATCH' });

    await page.goto('/#/perfil');
    await expect(page.getByRole('heading', { name: 'Mi perfil' })).toBeVisible();

    await page.getByRole('textbox', { name: 'Teléfono' }).fill('5599998888');
    await page.getByRole('button', { name: 'Guardar información' }).click();

    await expect(page.getByText('Información guardada correctamente.')).toBeVisible();
  });

  test('HU-AUTH-13: si el backend falla al guardar el perfil, se muestra el toast de error genérico', async ({ page }) => {
    // Refleja el comportamiento real observado: PATCH /customers/profile no está implementado
    // como tal en el backend (handler.py intenta int("profile") y falla) -> 404/500 real.
    await mockApi(page, '/customers/profile', { message: 'Ruta no encontrada', Error: 'NotFound' }, {
      method: 'PATCH',
      status: 404
    });

    await page.goto('/#/perfil');
    await page.getByRole('textbox', { name: 'Teléfono' }).fill('5588887777');
    await page.getByRole('button', { name: 'Guardar información' }).click();

    await expect(page.getByText('No se pudo guardar la información.')).toBeVisible();
  });
});

test.describe('HU-AUTH-14: Registro y actualización de CLABE interbancaria', () => {
  test.beforeEach(async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, `/customers/${USERS.cliente.userId}`, {
      customer: { customerId: USERS.cliente.userId, name: 'Ana Torres Ruiz', email: 'ana.torres@e2e.test', ownDocuments: [], documents: [] }
    }, { method: 'GET' });
  });

  test('HU-AUTH-14 / E2E-PROF-02: registrar una CLABE de 18 dígitos muestra la máscara con los últimos 4 dígitos', async ({ page }) => {
    await mockApi(page, '/customers/clabe', { ok: true, clabeLast4: '5678' }, { method: 'POST' });

    await page.goto('/#/perfil');
    await page.getByRole('textbox', { name: 'Nueva CLABE (18 dígitos)' }).fill('123456789012345678');
    await page.getByRole('button', { name: 'Actualizar CLABE' }).click();

    await expect(page.getByRole('heading', { name: 'Confirmar CLABE' })).toBeVisible();
    await page.getByRole('button', { name: 'Confirmar', exact: true }).click();

    await expect(page.getByText('CLABE guardada correctamente.')).toBeVisible();
    await expect(page.getByText('•••• •••• •••• 5678')).toBeVisible();
  });

  test('HU-AUTH-14 / E2E-PROF-03: una CLABE con longitud inválida se bloquea localmente antes de confirmar', async ({ page }) => {
    let clabeCalled = false;
    await page.route(`${API_BASE}/customers/clabe`, (route) => {
      clabeCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/perfil');
    await page.getByRole('textbox', { name: 'Nueva CLABE (18 dígitos)' }).fill('12345');
    await page.getByRole('button', { name: 'Actualizar CLABE' }).click();

    await expect(page.getByText('La CLABE debe tener 18 dígitos.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Confirmar CLABE' })).toHaveCount(0);
    expect(clabeCalled).toBe(false);
  });
});

test.describe('HU-AUTH-15: Carga de documentos propios (constancia/INE/CURP)', () => {
  test.beforeEach(async ({ page }) => {
    await seedSession(page, USERS.cliente);
    // getBusinessConfig (config.customerDocumentTypes) queda sin mockear a propósito: al fallar
    // con el 500 de blockUnmockedApi, el componente cae en su set por defecto de 3 documentos
    // (constancia/INE/CURP), que es exactamente lo que necesitan estos casos.
    await blockUnmockedApi(page);
    await mockApi(page, `/customers/${USERS.cliente.userId}`, {
      customer: { customerId: USERS.cliente.userId, name: 'Ana Torres Ruiz', email: 'ana.torres@e2e.test', ownDocuments: [], documents: [] }
    }, { method: 'GET' });
  });

  test('HU-AUTH-15 / E2E-PROF-04: subir un documento propio (INE) lo marca como cargado', async ({ page }) => {
    await mockApi(page, '/customers/documents', {
      customer: {
        customerId: USERS.cliente.userId,
        name: 'Ana Torres Ruiz',
        email: 'ana.torres@e2e.test',
        ownDocuments: [{
          id: 'doc-ine-001',
          docType: 'ine',
          name: 'ine-frente.png',
          uploadedAt: new Date().toISOString(),
          url: 'https://example.test/ine.png',
          type: 'image/png'
        }]
      }
    }, { method: 'POST' });

    await page.goto('/#/perfil');
    await expect(page.getByText('INE (frente y reverso)')).toBeVisible();

    await page.locator('#own-doc-ine').setInputFiles({
      name: 'ine-frente.png',
      mimeType: 'image/png',
      buffer: Buffer.from('fake-image-content')
    });
    const ineRow = page.locator('div.rounded-2xl.border.border-olive-20.bg-sand-200-90.p-4', {
      has: page.locator('#own-doc-ine')
    });
    await ineRow.getByRole('button', { name: 'Subir' }).click();

    await expect(page.getByText('INE (frente y reverso) subido correctamente.')).toBeVisible();
    await expect(ineRow.getByText(/Subido el/)).toBeVisible();
  });

  test('HU-AUTH-15 / E2E-PROF-05: un error del backend al subir el documento muestra el mensaje de error', async ({ page }) => {
    await mockApi(page, '/customers/documents', { message: 'Ruta no encontrada', Error: 'NotFound' }, {
      method: 'POST',
      status: 404
    });

    await page.goto('/#/perfil');
    await page.locator('#own-doc-curp').setInputFiles({
      name: 'curp.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 fake')
    });
    const curpRow = page.locator('div.rounded-2xl.border.border-olive-20.bg-sand-200-90.p-4', {
      has: page.locator('#own-doc-curp')
    });
    await curpRow.getByRole('button', { name: 'Subir' }).click();

    // El mensaje aparece dos veces: como error inline bajo el documento y como toast global.
    await expect(page.getByText('No se pudo subir el documento.').first()).toBeVisible();
    await expect(curpRow.getByText('No se pudo subir el documento.')).toBeVisible();
  });
});

test.describe('HU-AUTH-10: Cambio de contraseña autenticado desde el perfil', () => {
  test.beforeEach(async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, `/customers/${USERS.cliente.userId}`, {
      customer: { customerId: USERS.cliente.userId, name: 'Ana Torres Ruiz', email: 'ana.torres@e2e.test', ownDocuments: [], documents: [] }
    }, { method: 'GET' });
  });

  test('HU-AUTH-10 / E2E-AUTH-17: cambio de contraseña autenticado exitoso limpia el formulario', async ({ page }) => {
    await mockApi(page, '/auth/changepassword', {}, { method: 'POST' });

    await page.goto('/#/perfil');
    await page.getByPlaceholder('Tu contraseña actual').fill('ClaveActual123!');
    await page.getByPlaceholder('Mínimo 8 caracteres').fill('ClaveNueva456!');
    await page.getByPlaceholder('Repite la nueva contraseña').fill('ClaveNueva456!');
    await page.getByRole('button', { name: 'Cambiar contraseña' }).click();

    await expect(page.getByText('Contraseña actualizada correctamente.')).toBeVisible();
    await expect(page.getByPlaceholder('Tu contraseña actual')).toHaveValue('');
  });

  test('HU-AUTH-10 / E2E-AUTH-18: cambio con contraseña actual incorrecta muestra el error del backend', async ({ page }) => {
    await mockApi(page, '/auth/changepassword', { message: 'La contraseña actual no es correcta.' }, {
      method: 'POST',
      status: 400
    });

    await page.goto('/#/perfil');
    await page.getByPlaceholder('Tu contraseña actual').fill('ClaveIncorrecta!');
    await page.getByPlaceholder('Mínimo 8 caracteres').fill('ClaveNueva456!');
    await page.getByPlaceholder('Repite la nueva contraseña').fill('ClaveNueva456!');
    await page.getByRole('button', { name: 'Cambiar contraseña' }).click();

    await expect(page.getByText('La contraseña actual no es correcta.')).toBeVisible();
  });

  test('HU-AUTH-10 / E2E-AUTH-19: una nueva contraseña de menos de 8 caracteres bloquea el envío', async ({ page }) => {
    let changePasswordCalled = false;
    await page.route(`${API_BASE}/auth/changepassword`, (route) => {
      changePasswordCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/perfil');
    await page.getByPlaceholder('Tu contraseña actual').fill('ClaveActual123!');
    await page.getByPlaceholder('Mínimo 8 caracteres').fill('corta');
    await page.getByPlaceholder('Repite la nueva contraseña').fill('corta');
    await page.getByRole('button', { name: 'Cambiar contraseña' }).click();

    await expect(page.getByText('La nueva contraseña debe tener al menos 8 caracteres.')).toBeVisible();
    expect(changePasswordCalled).toBe(false);
  });

  test('HU-AUTH-10: la contraseña actual vacía exige el campo sin llamar al backend', async ({ page }) => {
    let changePasswordCalled = false;
    await page.route(`${API_BASE}/auth/changepassword`, (route) => {
      changePasswordCalled = true;
      return route.fulfill({ status: 500, body: '{}' });
    });

    await page.goto('/#/perfil');
    await page.getByPlaceholder('Mínimo 8 caracteres').fill('ClaveNueva456!');
    await page.getByPlaceholder('Repite la nueva contraseña').fill('ClaveNueva456!');
    await page.getByRole('button', { name: 'Cambiar contraseña' }).click();

    await expect(page.getByText('Ingresa tu contraseña actual.')).toBeVisible();
    expect(changePasswordCalled).toBe(false);
  });
});

test.describe('HU-AUTH-16: Visualización de los datos del patrocinador', () => {
  test('HU-AUTH-16 / E2E-PROF-06: el patrocinador se muestra en el dashboard, no en /perfil (nota de la matriz)', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, '/customers/dashboard', {
      isGuest: false,
      settings: { cutoffDay: 25, cutoffHour: 23, cutoffMinute: 59, userCode: 'ABC123', networkGoal: 300 },
      goals: [],
      networkMembers: [],
      buyAgainIds: [],
      commissions: null,
      notifications: [],
      sponsor: { name: 'Jorge Referidor', email: 'jorge@e2e.test', phone: '5215555555555', isDefault: false }
    }, { method: 'GET' });
    await mockApi(page, '/catalog/catalog', { products: [], productOfMonth: null }, { method: 'GET' });

    await page.goto('/#/dashboard');
    await expect(page.getByText('Patrocinador')).toBeVisible();
    await expect(page.getByText('Jorge Referidor')).toBeVisible();

    // En /perfil no existe ninguna sección de patrocinador (confirmado en el código fuente).
    await mockApi(page, `/customers/${USERS.cliente.userId}`, {
      customer: { customerId: USERS.cliente.userId, name: 'Ana', email: 'ana@e2e.test', ownDocuments: [], documents: [] }
    }, { method: 'GET' });
    await page.goto('/#/perfil');
    await expect(page.getByText('Patrocinador')).toHaveCount(0);
  });
});

test.describe('HU-AUTH-17: Aviso de privacidad en primer acceso', () => {
  test('HU-AUTH-17 / E2E-PROF-07: el aviso de privacidad se muestra en el primer acceso y se acepta una sola vez', async ({ page }) => {
    // Nota de trazabilidad: docs/hu/01-hu-auth-registro-perfil.md marca esta HU como "funcionalidad
    // ausente" (ingeniería inversa contra una versión previa del código). El componente
    // PrivacyNoticeComponent (src/app/components/privacy-notice) SÍ existe y SÍ bloquea la app
    // en el primer acceso: este test documenta el comportamiento REAL, vigente, del código actual.
    await blockUnmockedApi(page);

    await page.goto('/#/login');
    await expect(page.getByRole('heading', { name: 'Aviso de Privacidad' })).toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem('privacy-notice-accepted-v1'))).toBeNull();

    await page.getByRole('button', { name: 'Entendido y acepto' }).click();

    await expect(page.getByRole('heading', { name: 'Aviso de Privacidad' })).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.getItem('privacy-notice-accepted-v1'))).toBe('true');

    // Al recargar, ya no debe volver a aparecer.
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Aviso de Privacidad' })).toHaveCount(0);
  });
});

test.describe('HU-AUTH-18: Direcciones de envío del cliente (gestión fuera del perfil)', () => {
  test('HU-AUTH-18: /perfil no expone ninguna gestión de direcciones de envío', async ({ page }) => {
    await seedSession(page, USERS.cliente);
    await blockUnmockedApi(page);
    await mockApi(page, `/customers/${USERS.cliente.userId}`, {
      customer: { customerId: USERS.cliente.userId, name: 'Ana', email: 'ana@e2e.test', ownDocuments: [], documents: [] }
    }, { method: 'GET' });

    await page.goto('/#/perfil');
    await expect(page.getByRole('heading', { name: 'Mi perfil' })).toBeVisible();

    // La gestión de direcciones vive en /carrito, no en /perfil (ver HU-AUTH-18).
    await expect(page.getByText(/Direcci(o|ó)n de env(i|í)o/i)).toHaveCount(0);
    await expect(page.getByRole('heading', { name: /Direcci/i })).toHaveCount(0);
  });
});

// NO AUTOMATIZADAS:
// - E2E-REF-02 (afiliado visible en la red del patrocinador) y E2E-REF-11/12 (notificación al
//   patrocinador / persistencia de leaderId en BD): requieren inspeccionar el dashboard/red del
//   patrocinador o el estado en base de datos, fuera del alcance de "Autenticación, Registro y
//   Perfil" ejercitable puramente desde el navegador del nuevo registrante.
// - E2E-REF-04 (registro vía /tienda/:refToken) y E2E-SHOP-06: pertenecen al dominio Tienda (SHOP),
//   no se automatizan aquí.
// - E2E-REF-09/E2E-REF-10 (generación y colisión de código de referido propio tipo
//   {Nombre}-{Iniciales}): esa lógica no existe en el backend real (`handler.py`); no hay ningún
//   flujo de UI que la ejercite.
// - E2E-REF-14 (prevención de ciclo de patrocinio): es una operación de administración
//   (reasignar líder), corresponde al dominio ADM, no a Registro/Perfil.
// - HU-AUTH-07 (bloqueo por email no verificado) y HU-AUTH-09/HU-AUTH-10 tal como describe la
//   matriz SÍ se cubren en auth.spec.ts, pero vía mocks: el backend real (`handler.py`) no
//   implementa `/auth/resend-email-confirmation` ni el mensaje de bloqueo, por lo que estos
//   flujos son irreproducibles contra el ambiente real (solo documentados como comportamiento
//   esperado del frontend).
