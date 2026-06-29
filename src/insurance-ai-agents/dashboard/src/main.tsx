import React from 'react'
import ReactDOM from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import App from './App'
import VoiceOperatorView from './components/VoiceOperatorView'
import { msalInstance, msalReady, AUTH_ENABLED } from './auth/msalConfig'
import './index.css'

/** Detect special standalone routes that should bypass the main app shell.
 *  We use a tiny query-string router because the project doesn't depend on
 *  react-router and the only standalone view today is the live operator
 *  monitoring window (opened via window.open from the auto-demo so the
 *  customer call modal and the operator dashboard can be visible side by
 *  side). */
function resolveStandaloneRoute(): { kind: 'voice-operator'; sessionId: string } | null {
  try {
    const url = new URL(window.location.href);
    if (url.searchParams.get('view') === 'voice-operator') {
      const sessionId = url.searchParams.get('session');
      if (sessionId) return { kind: 'voice-operator', sessionId };
    }
  } catch {
    /* noop */
  }
  return null;
}

async function bootstrap() {
  const standalone = resolveStandaloneRoute();
  if (standalone?.kind === 'voice-operator') {
    // The operator window does NOT need MSAL or the main app shell — it
    // is a passive observer of an active session and is opened by the
    // already-authenticated parent window.
    ReactDOM.createRoot(document.getElementById('root')!).render(
      <React.StrictMode>
        <VoiceOperatorView sessionId={standalone.sessionId} />
      </React.StrictMode>,
    )
    return;
  }

  if (AUTH_ENABLED) {
    await msalReady;
  }
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <MsalProvider instance={msalInstance}>
        <App />
      </MsalProvider>
    </React.StrictMode>,
  )
}

bootstrap();
