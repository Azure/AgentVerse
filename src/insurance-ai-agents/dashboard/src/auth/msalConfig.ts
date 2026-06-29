/**
 * Configuración MSAL para Entra ID.
 *
 * - Si VITE_AUTH_ENABLED !== 'true' el frontend funciona en modo "demo abierto"
 *   (sin login) y se asume rol Operator (compatibilidad con la demo previa).
 * - Roles esperados (App Roles del app registration):
 *     Customer.Submit  → tab "Cliente"
 *     Operator.Review  → tabs Operario / Estadísticas / Clientes / Pólizas / Seguridad / Gobernanza
 */
import { Configuration, LogLevel, PublicClientApplication } from '@azure/msal-browser';

export const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true';

const CLIENT_ID = import.meta.env.VITE_AUTH_CLIENT_ID || '4e593597-088c-404c-984c-203259ff7dbe';
const TENANT_ID = import.meta.env.VITE_AUTH_TENANT_ID || '763b21d6-9a2e-4d90-88f9-d3c5cc8dba90';

// Scope expuesto por la propia API (App reg con identifier URI api://{CLIENT_ID}).
// Para flujos delegated en SPAs se usa el scope nominal `access_as_user`, no
// `.default` (que está pensado para client-credentials / admin consent).
export const API_SCOPES: string[] = [`api://${CLIENT_ID}/access_as_user`];
// Login mínimo: solo OIDC (openid+profile). Esto no requiere consent extra ni
// scopes de Graph, así que el primer login con un usuario nuevo es 1 click.
// El access token de la API se pide perezosamente vía acquireApiToken().
export const LOGIN_SCOPES: string[] = ['openid', 'profile'];

export const ROLE_CUSTOMER = 'Customer.Submit';
export const ROLE_OPERATOR = 'Operator.Review';

export const msalConfig: Configuration = {
  auth: {
    clientId: CLIENT_ID,
    authority: `https://login.microsoftonline.com/${TENANT_ID}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Warning,
      loggerCallback: (level, message) => {
        if (level <= LogLevel.Warning) console.warn('[msal]', message);
      },
      piiLoggingEnabled: false,
    },
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

// Inicialización requerida en MSAL v3+ antes de cualquier API call.
export const msalReady: Promise<void> = msalInstance.initialize().then(() => {
  // Procesar redirect (no-op si usamos popup)
  return msalInstance.handleRedirectPromise().then(() => undefined);
});

/**
 * Adquiere un access token para llamar a la API. Definida aquí (no en
 * useAuth.ts) para evitar la indirección con React y garantizar que cualquier
 * import use la misma instancia singleton de MSAL.
 *
 * Devuelve null si auth está desactivado, no hay cuenta, o si MSAL no puede
 * obtener el token de forma silenciosa. NO abrimos popup desde aquí.
 */
export async function acquireApiToken(): Promise<string | null> {
  if (!AUTH_ENABLED) return null;
  await msalReady;
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length === 0) {
    console.warn('[auth] acquireApiToken: getAllAccounts()=[] → sin Bearer');
    return null;
  }
  try {
    const result = await msalInstance.acquireTokenSilent({
      scopes: API_SCOPES,
      account: accounts[0],
    });
    return result.accessToken;
  } catch (err) {
    console.warn('[auth] acquireTokenSilent failed:', err);
    return null;
  }
}
