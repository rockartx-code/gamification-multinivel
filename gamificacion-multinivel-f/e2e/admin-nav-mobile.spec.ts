import { test, expect, seedSession, USERS, blockUnmockedApi } from './support/fixtures';
import { mockAdminBaseline } from './support/admin-mocks';

// Cobertura del rediseño de navegación admin en móvil (ver docs/ux/analisis-ui-ux-2026-08.md,
// "Hallazgo transversal: navegación admin en móvil" — antes una barra inferior fija con 11-12
// botones ocupaba ~41% del viewport de forma permanente; ahora se reemplaza por el mismo patrón
// hamburguesa + ui-sidebar-nav compacto que ya usa el Dashboard del asociado).
test.describe('Panel Admin — navegación móvil', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('la barra inferior fija fue reemplazada por un menú hamburguesa', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');

    // La antigua barra inferior fija (#bottomBar) ya no existe en el DOM.
    await expect(page.locator('#bottomBar')).toHaveCount(0);

    // El botón hamburguesa es visible en viewport móvil.
    const hamburger = page.getByRole('button', { name: 'Navegación' });
    await expect(hamburger).toBeVisible();
  });

  test('el menú hamburguesa despliega los destinos y navega al seleccionar uno', async ({ page }) => {
    await seedSession(page, USERS.admin);
    await blockUnmockedApi(page);
    await mockAdminBaseline(page);

    await page.goto('/#/admin');

    const hamburger = page.getByRole('button', { name: 'Navegación' });
    const mobileNavPanel = page.locator('div.lg\\:hidden ui-sidebar-nav');

    // Panel cerrado por defecto.
    await expect(mobileNavPanel).toBeHidden();

    await hamburger.click();
    await expect(mobileNavPanel).toBeVisible();
    await expect(mobileNavPanel.getByRole('button', { name: 'Clientes' })).toBeVisible();

    // Sustituto móvil del panel "Estado del mes" (antes solo existía en la <aside> de desktop).
    await expect(page.getByText('Estado del mes').first()).toBeVisible();

    await mobileNavPanel.getByRole('button', { name: 'Clientes' }).click();

    // Navegó a la vista y el panel se cierra solo tras seleccionar un destino.
    await expect(page.getByText('Clientes (todos los niveles)')).toBeVisible();
    await expect(mobileNavPanel).toBeHidden();
  });
});
