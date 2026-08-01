import { test, expect, seedSession, acceptPrivacyNotice, USERS } from './support/fixtures';

// Smoke del andamiaje: verifica que la app levanta, el routing hash funciona
// y que la siembra de sesión por localStorage es reconocida por los guards.

test('la app carga y muestra la pantalla de login', async ({ page }) => {
  // La página de login NO usa <form>: inputs sueltos con ngModel.
  // OJO: ui-form-field replica atributos (placeholder) en el host — usar getByRole, no getByPlaceholder.
  await acceptPrivacyNotice(page);
  await page.goto('/#/login');
  await expect(page.getByPlaceholder('Tu contraseña')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Correo electrónico' })).toBeVisible();
});

test('en primera visita aparece el Aviso de Privacidad', async ({ page }) => {
  await page.goto('/#/login');
  await expect(page.getByRole('heading', { name: 'Aviso de Privacidad' })).toBeVisible();
});

test('con sesión de cliente sembrada, /dashboard no redirige a login', async ({ page }) => {
  await seedSession(page, USERS.cliente);
  await page.goto('/#/dashboard');
  await expect(page).not.toHaveURL(/#\/login/);
});

test('sin sesión, /admin redirige fuera del panel', async ({ page }) => {
  await page.goto('/#/admin');
  await expect(page).not.toHaveURL(/#\/admin$/);
});
