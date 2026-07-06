/**
 * MSAL configuration for Entra ID.
 *
 * - If VITE_AUTH_ENABLED !== 'true' the frontend runs in "open demo" mode
 *   (no login) and assumes the Operator role (compatible with the previous demo).
 * - Expected roles (App Roles of the app registration):
 *     Customer.Submit  → "Customer" tab
 *     Operator.Review  → tabs Operator / Statistics / Customers / Policies / Security / Governance
 */
import { Configuration, LogLevel, PublicClientApplication } from '@azure/msal-browser';

export const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED === 'true';

const CLIENT_ID = import.meta.env.VITE_AUTH_CLIENT_ID || '4e593597-088c-404c-984c-203259ff7dbe';
const TENANT_ID = import.meta.env.VITE_AUTH_TENANT_ID || '763b21d6-9a2e-4d90-88f9-d3c5cc8dba90';

// Scope exposed by the API itself (App reg with identifier URI api://{CLIENT_ID}).
// For delegated flows in SPAs we use the nominal scope `access_as_user`, not
// `.default` (which is meant for client-credentials / admin consent).
export const API_SCOPES: string[] = [`api://${CLIENT_ID}/access_as_user`];
// Minimal login: only OIDC (openid+profile). This requires no extra consent nor
// Graph scopes, so the first login for a new user is a single click.
// The API access token is requested lazily via acquireApiToken().
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

// Initialization required in MSAL v3+ before any API call.
export const msalReady: Promise<void> = msalInstance.initialize().then(() => {
  // Process redirect (no-op if we use popup)
  return msalInstance.handleRedirectPromise().then(() => undefined);
});

/**
 * Acquires an access token to call the API. Defined here (not in
 * useAuth.ts) to avoid the React indirection and guarantee that any
 * import uses the same MSAL singleton instance.
 *
 * Returns null if auth is disabled, there is no account, or if MSAL cannot
 * obtain the token silently. We do NOT open a popup from here.
 */
export async function acquireApiToken(): Promise<string | null> {
  if (!AUTH_ENABLED) return null;
  await msalReady;
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length === 0) {
    console.warn('[auth] acquireApiToken: getAllAccounts()=[] → no Bearer');
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
