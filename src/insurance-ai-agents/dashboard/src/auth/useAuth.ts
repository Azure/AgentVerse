/**
 * Auth hooks and helpers: role extraction, viewMode and forcing the access
 * token cache after login.
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import { useMsal, useIsAuthenticated } from '@azure/msal-react';
import type { AccountInfo } from '@azure/msal-browser';
import { AUTH_ENABLED, API_SCOPES, LOGIN_SCOPES, ROLE_CUSTOMER, ROLE_OPERATOR } from './msalConfig';

// Re-export for compatibility with code that already imports from here.
export { acquireApiToken } from './msalConfig';

export type ViewMode = 'customer' | 'operator';

export interface AuthState {
  enabled: boolean;
  authenticated: boolean;
  account: AccountInfo | null;
  roles: string[];
  isCustomer: boolean;
  isOperator: boolean;
  /** Active view (when the user has both roles they can toggle). */
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  /** Customer identifier — we use the token UPN/email for the demo. */
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

  // If the role set changes (login/logout) we reset the viewMode.
  useEffect(() => {
    setViewModeState(isOperator ? 'operator' : 'customer');
  }, [isOperator, isCustomer]);

  const setViewMode = useCallback((m: ViewMode) => {
    if (m === 'operator' && !isOperator) return;
    if (m === 'customer' && !isCustomer) return;
    setViewModeState(m);
  }, [isCustomer, isOperator]);

  const login = useCallback(async () => {
    // We request OIDC + the API scope in the same popup. This way the consent
    // ('access_as_user') is resolved on the first login and afterwards
    // acquireTokenSilent works without opening more popups.
    await instance.loginPopup({ scopes: [...LOGIN_SCOPES, ...API_SCOPES] });
  }, [instance]);

  const logout = useCallback(async () => {
    await instance.logoutPopup();
  }, [instance]);

  // For the demo: we use the username (UPN/email) as customer_id.
  // In production, email → customer_id would be mapped in the backend.
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
