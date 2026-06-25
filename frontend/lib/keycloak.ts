import Keycloak from "keycloak-js"

let keycloak: Keycloak | null = null
let initPromise: Promise<boolean> | null = null

function getKeycloak(): Keycloak {
  if (!keycloak) {
    keycloak = new Keycloak({
      url: process.env.NEXT_PUBLIC_KEYCLOAK_URL!,
      realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM!,
      clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID!,
    })
  }
  return keycloak
}

// Memoize init so React Strict Mode's double-effect doesn't re-init (which throws).
export function initKeycloak(): { kc: Keycloak; ready: Promise<boolean> } {
  const kc = getKeycloak()
  if (!initPromise) {
    initPromise = kc.init({
      // Redirect to the Keycloak login page immediately when there is no session.
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    })
  }
  return { kc, ready: initPromise }
}
