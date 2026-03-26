# Envia API --- Cotización de Envío (Implementación Mínima)

## Objetivo

Implementar una función que permita cotizar envíos entre dos códigos
postales usando la API de Envia.

## Endpoint

POST https://api-test.envia.com/ship/rate/

Headers: - Authorization: Bearer `<ENVIA_TOKEN>`{=html} - Content-Type:
application/json

## Input

type QuoteInput = { countryFrom: string; zipFrom: string; countryTo:
string; zipTo: string; weightKg: number; lengthCm: number; widthCm:
number; heightCm: number; };

## Implementación

``` ts
export async function quoteShipment(input) {
  const token = process.env.ENVIA_TOKEN;
  if (!token) throw new Error("Missing ENVIA_TOKEN");

  const body = {
    shipment: {
      carrier: "",
      service: "",
      type: 1,
      origin: {
        country: input.countryFrom,
        postalCode: input.zipFrom,
      },
      destination: {
        country: input.countryTo,
        postalCode: input.zipTo,
      },
      packages: [
        {
          content: "Mercancia general",
          amount: 1,
          type: "box",
          dimensions: {
            length: input.lengthCm,
            width: input.widthCm,
            height: input.heightCm,
          },
          weight: input.weightKg,
        },
      ],
    },
  };

  const res = await fetch("https://api-test.envia.com/ship/rate/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const data = await res.json();

  return (data.data || []).map(rate => ({
    carrier: rate.carrier || null,
    service: rate.service || null,
    price: rate.total || null,
    currency: rate.currency || null,
    transitDays: rate.delivery_days || null,
  }));
}
```

## Ejemplo

``` ts
quoteShipment({
  countryFrom: "MX",
  zipFrom: "64060",
  countryTo: "MX",
  zipTo: "44100",
  weightKg: 2.5,
  lengthCm: 20,
  widthCm: 15,
  heightCm: 10,
});
```
