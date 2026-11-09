// Período de acceso gratis para todos (sin código). Se cambia con la variable GRATIS_HASTA en Vercel.
export const GRATIS_HASTA = process.env.GRATIS_HASTA || "2026-12-10T02:59:59Z"; // 9 de diciembre, 23:59 en Chile
export function accesoGratis() {
  return Date.now() < Date.parse(GRATIS_HASTA);
}
