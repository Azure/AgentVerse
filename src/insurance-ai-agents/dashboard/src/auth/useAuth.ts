/**
 * Hooks y helpers de auth: extracción de roles, viewMode y forzado de cache
 * del access token tras login.
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import { useMsal, useIsAuthenticated } from '@azure/msal-react';
import type { AccountInfo } from '@azure/msal-browser';
import { AUTH_ENABLED, API_SCOPES, LOGIN_SCOPES, ROLE_CUSTOMER, ROLE_OPERATOR } from './msalConfig';

// Re-export para compatibilidad con código que ya importa desde aquí.
export { acquireApiToken } from './msalConfig';

export type ViewMode = 'customer' | 'operator';

export interface AuthState {
  enabled: boolean;
  authenticated: boolean;
  account: AccountInfo | null;
  roles: string[];
  isCustomer: boolean;
  isOperator: boolean;
  /** Vista activa (cuando el usuario tiene ambos roles puede alternar). */
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  /** Identificador del cliente — usamos el UPN/email del token para el demo. */
  customerId: string;
}

function rolesFromAccount(account: AccountInfo | null): string[] {
  if (!account || !account.idTokenClaims) return [];
  const roles = (account.idTokenClaims as { roles?: string[] }).roles;
  return Array.isArray(roles) ? roles : [];
}

export function useAuth(): AuthState {
  const { instance, accounts } = useMsal();
  const authenticated = useIsAuthenticated();
  const account = accounts[0] || null;
  const roles = useMemo(() => rolesFromAccount(account), [account]);

  const isCustomer = !AUTH_ENABLED || roles.includes(ROLE_CUSTOMER);
  const isOperator = !AUTH_ENABLED || roles.includes(ROLE_OPERATOR);

  const defaultMode: ViewMode = isOperator ? 'operator' : 'customer';
  const [viewMode, setViewModeState] = useState<ViewMode>(defaultMode);

  // Si cambia el set de roles (login/logout) reseteamos el viewMode.
  useEffect(() => {
    setViewModeState(isOperator ? 'operator' : 'customer');
  }, [isOperator, isCustomer]);

  const setViewMode = useCallback((m: ViewMode) => {
    if (m === 'operator' && !isOperator) return;
    if (m === 'customer' && !isCustomer) return;
    setViewModeState(m);
  }, [isCustomer, isOperator]);

  const login = useCallback(async () => {
    // Pedimos OIDC + el scope de la API en la misma popup. Así el consent
    // ('access_as_user') se resuelve en el primer login y luego
    // acquireTokenSilent funcionará sin abrir más popups.
    await instance.loginPopup({ scopes: [...LOGIN_SCOPES, ...API_SCOPES] });
  }, [instance]);

  const logout = useCallback(async () => {
    await instance.logoutPopup();
  }, [instance]);

  // Para la demo: usamos el username (UPN/email) como customer_id.
  // En producción se mapearía email → customer_id en backend.
  const customerId = AUTH_ENABLED && account
    ? account.username
    : 'CUST-1001';

  return {
    enabled: AUTH_ENABLED,
    authenticated: !AUTH_ENABLED || authenticated,
    account,
    roles,
    isCustomer,
    isOperator,
    viewMode,
    setViewMode,
    login,
    logout,
    customerId,
  };
}
