import { test, expect, acceptPrivacyNotice, mockApi, blockUnmockedApi } from './support/fixtures';

// Dominio: Landing pública (/#/landing) — validar que los porcentajes de comisión,
// descuentos y niveles/rangos mostrados vienen de la configuración pública del
// backend (GET /catalog/config/public, catalog_lambda.handle_public_config) en
// lugar de estar hardcodeados en el componente, con fallback a valores de negocio
// actuales si el endpoint falla.
//
// Quirks aplicados (docs/qa/05-cobertura-e2e-playwright-y-hallazgos.md §7):
// - Hash routing: navegar a `/#/landing`. Puerto dedicado 4300.
// - blockUnmockedApi(page) se registra ANTES que los mocks específicos: page.route
//   evalúa handlers en orden LIFO, así que el catch-all no debe tapar los mocks.
// - App zoneless: LandingComponent llama cdr.detectChanges() tras cada suscripción
//   async (loadBusinessConfig/loadFeaturedProduct), así que basta esperar a que el
//   contenido objetivo sea visible (Playwright ya reintenta hasta que aparece).
//
// La landing sin :idSponsor no carga sponsor (hasRealSponsor=false), por lo que
// renderiza el layout completo ("MODO SIN PATROCINADOR") que incluye las secciones
// de Descuentos Progresivos, Comisiones de Red y Premios a tu Excelencia.

const CATALOG_STUB = {
  products: [],
  productOfMonth: null
};

function configResponse(config: unknown) {
  return { config };
}

test.describe('Landing pública: datos desde configuración', () => {
  test('refleja los valores de descuentos, comisiones y rangos que devuelve /catalog/config/public', async ({
    page
  }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, /\/catalog\/catalog(\?.*)?$/, CATALOG_STUB);
    await mockApi(page, /\/catalog\/config\/public(\?.*)?$/, configResponse({
      rewards: {
        discountTiers: [
          { min: 0, max: 500, rate: 0.05 },
          { min: 500, max: null, rate: 0.15 }
        ],
        commissionLevels: [
          { rate: 0.2, reqActiveDirects: 0, reqPersonalPC: 0, reqLines: 0, reqPCPerLine: 0 }
        ],
        activationNetMin: 2500
      },
      bonuses: {
        vpConfig: { mxnPerVp: 77, maxNetworkLevels: 5 },
        rankThresholds: [
          { rank: 'RANGOE2E', vgMin: 1234, requiredDirects: 3 }
        ],
        rules: [
          {
            id: 'inicio_rapido',
            name: 'Bono Rapido E2E',
            active: true,
            conditions: [{ type: 'first_30_days' }, { type: 'vg_min', value: 600 }],
            rewards: [{ type: 'cash_mxn', amount: 9999 }],
            cooldown: 'once',
            notes: 'Nota de prueba E2E'
          },
          {
            id: 'bono_rango_e2e',
            name: 'Bono Mensual RANGOE2E',
            active: true,
            rank: 'RANGOE2E',
            conditions: [{ type: 'vg_min', value: 1234 }, { type: 'consecutive_months', value: 4 }],
            rewards: [{ type: 'monthly_cash', amount: 4321 }],
            cooldown: 'monthly',
            notes: 'Bono mensual de prueba'
          }
        ]
      }
    }));

    await page.goto('/#/landing');

    // Sección de descuentos progresivos: debe mostrar los tiers de la config mockeada,
    // no los defaults hardcodeados del componente (0/10/20/30/40%).
    const discountSection = page.locator('section', { has: page.getByRole('heading', { name: 'Descuentos Progresivos' }) });
    await expect(discountSection.getByText('De $0 a $500')).toBeVisible();
    await expect(discountSection.getByText('5% OFF', { exact: true })).toBeVisible();
    await expect(discountSection.getByText('$500 o más')).toBeVisible();
    await expect(discountSection.getByText('15% OFF')).toBeVisible();

    // Comisiones de red: 1 VP = $77 MXN (del vpConfig mockeado) y la generación 1 al 20%.
    // Nota: el pipe `number:'1.0-1'` omite el decimal cuando es .0, así que 0.2*100 se
    // muestra como "20%" (no "20.0%").
    const commissionSection = page.locator('section', { has: page.getByRole('heading', { name: 'Comisiones de Red' }) });
    await expect(commissionSection.getByText('1 VP = $77 MXN netos (sin IVA ni envío)')).toBeVisible();
    await expect(commissionSection.getByText('Gen 1')).toBeVisible();
    await expect(commissionSection.getByText('20%', { exact: true })).toBeVisible();

    // Bono de Inicio Rápido: nombre y monto vienen de la regla mockeada.
    await expect(page.getByRole('heading', { name: 'Bono Rapido E2E' })).toBeVisible();
    await expect(page.getByText('$9,999 MXN')).toBeVisible();

    // Rango mockeado (RANGOE2E): nombre, VG mínimo formateado y la restricción de
    // referidos directos (feature nueva: config.bonuses.rankThresholds[].requiredDirects).
    await expect(page.getByRole('heading', { name: 'RANGOE2E' })).toBeVisible();
    await expect(page.getByText('1,234 puntos VG')).toBeVisible();
    await expect(page.getByText('+ 3 referidos directos')).toBeVisible();
    await expect(page.getByText('$4,321 MXN/mes')).toBeVisible();
  });

  test('si /catalog/config/public falla, cae a los valores de negocio actuales en vez de dejar tablas vacías', async ({
    page
  }) => {
    await acceptPrivacyNotice(page);
    await blockUnmockedApi(page);
    await mockApi(page, /\/catalog\/catalog(\?.*)?$/, CATALOG_STUB);
    await mockApi(page, /\/catalog\/config\/public(\?.*)?$/, { message: 'boom' }, { status: 500 });

    await page.goto('/#/landing');

    // Fallback de discountTiers (_default_app_config: 0-1000@0%, 1000-2000@10%, ...).
    const discountSection = page.locator('section', { has: page.getByRole('heading', { name: 'Descuentos Progresivos' }) });
    await expect(discountSection.getByText('De $0 a $1,000')).toBeVisible();
    await expect(discountSection.getByText('10% OFF')).toBeVisible();
    await expect(discountSection.getByText('$6,000 o más')).toBeVisible();
    await expect(discountSection.getByText('40% OFF')).toBeVisible();

    // Fallback de commissionLevels: Gen 1 al 10%, sin requisito de directos ("Activo").
    const commissionSection = page.locator('section', { has: page.getByRole('heading', { name: 'Comisiones de Red' }) });
    await expect(commissionSection.getByText('Gen 1')).toBeVisible();
    await expect(commissionSection.getByText('10%', { exact: true })).toBeVisible();
    await expect(commissionSection.getByRole('cell', { name: 'Activo' })).toBeVisible();

    // Fallback de rankThresholds (getter local: ORO/PLATINO/DIAMANTE) — la sección de
    // rangos sigue mostrando algo coherente en vez de quedar vacía.
    await expect(page.getByRole('heading', { name: 'ORO' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'PLATINO' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'DIAMANTE' })).toBeVisible();

    // Sin reglas de bono (rules=[] al no haber config), no debe aparecer el bono de
    // inicio rápido, y cada rango cae al placeholder "Próximamente".
    await expect(page.getByText('Bono de Inicio Rápido disponible')).toHaveCount(0);
    await expect(page.getByText('Próximamente').first()).toBeVisible();
  });
});
