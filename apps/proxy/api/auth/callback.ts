/**
 * GET /api/auth/callback
 *
 * GitHub OAuth callback handler.
 * Exchanges authorization code for access token and creates session.
 */

import {
  validateState,
  exchangeCodeForToken,
  createSession,
} from "../../lib/auth";

export const config = {
  runtime: "edge",
};

export default async function handler(request: Request): Promise<Response> {
  if (request.method !== "GET") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const url = new URL(request.url);
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const error = url.searchParams.get("error");
    const errorDescription = url.searchParams.get("error_description");

    // Handle OAuth errors
    if (error) {
      return createErrorResponse(
        error,
        errorDescription || "Authorization failed",
      );
    }

    // Validate required parameters
    if (!code || !state) {
      return createErrorResponse(
        "invalid_request",
        "Missing code or state parameter",
      );
    }

    // Validate state for CSRF protection
    const storedRedirect = await validateState(state);
    if (!storedRedirect) {
      return createErrorResponse(
        "invalid_state",
        "Invalid or expired state parameter",
      );
    }

    // Exchange code for access token
    const accessToken = await exchangeCodeForToken(code);

    // Create session
    const { sessionToken, session } = await createSession(accessToken);

    // Check if this is a CLI login (redirect to special page) or web flow
    if (storedRedirect.startsWith("/cli-callback")) {
      // CLI flow: show success page with token
      return createCliSuccessResponse(sessionToken, session.username);
    }

    // Web flow: redirect with token in fragment (not query string for security)
    const redirectUrl = new URL(storedRedirect, url.origin);

    // Return HTML that stores token and redirects
    return createWebSuccessResponse(
      sessionToken,
      session.username,
      redirectUrl.toString(),
    );
  } catch (error) {
    console.error("OAuth callback error:", error);
    return createErrorResponse(
      "server_error",
      error instanceof Error ? error.message : "Authentication failed",
    );
  }
}

function createErrorResponse(error: string, description: string): Response {
  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Authentication Failed - Rocket CLI</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0d1117; color: #c9d1d9; }
    .container { text-align: center; padding: 40px; max-width: 400px; }
    .icon { font-size: 64px; margin-bottom: 20px; }
    h1 { color: #f85149; margin-bottom: 10px; }
    p { color: #8b949e; margin-bottom: 20px; }
    code { background: #161b22; padding: 2px 6px; border-radius: 4px; color: #f0883e; }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">❌</div>
    <h1>Authentication Failed</h1>
    <p>${escapeHtml(description)}</p>
    <p>Error code: <code>${escapeHtml(error)}</code></p>
    <p>You can close this window and try again.</p>
  </div>
</body>
</html>`;

  return new Response(html, {
    status: 400,
    headers: { "Content-Type": "text/html" },
  });
}

function createCliSuccessResponse(token: string, username: string): Response {
  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Login Successful - Rocket CLI</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0d1117; color: #c9d1d9; }
    .container { text-align: center; padding: 40px; max-width: 500px; }
    .icon { font-size: 64px; margin-bottom: 20px; }
    h1 { color: #3fb950; margin-bottom: 10px; }
    p { color: #8b949e; margin-bottom: 20px; }
    .username { color: #58a6ff; font-weight: bold; }
    .token-box { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin: 20px 0; word-break: break-all; font-family: monospace; font-size: 12px; }
    .copy-btn { background: #238636; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-top: 10px; }
    .copy-btn:hover { background: #2ea043; }
    .note { font-size: 12px; color: #6e7681; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">🚀</div>
    <h1>Welcome, <span class="username">${escapeHtml(username)}</span>!</h1>
    <p>You've successfully logged in to Rocket CLI.</p>
    <p>If the CLI didn't automatically receive your token, copy it below:</p>
    <div class="token-box" id="token">${escapeHtml(token)}</div>
    <button class="copy-btn" onclick="copyToken()">📋 Copy Token</button>
    <p class="note">Paste this token when prompted in your terminal, or you can close this window.</p>
  </div>
  <script>
    function copyToken() {
      navigator.clipboard.writeText('${token}');
      document.querySelector('.copy-btn').textContent = '✓ Copied!';
    }
    // Auto-copy for convenience
    if (navigator.clipboard) {
      navigator.clipboard.writeText('${token}').catch(() => {});
    }
  </script>
</body>
</html>`;

  return new Response(html, {
    status: 200,
    headers: { "Content-Type": "text/html" },
  });
}

function createWebSuccessResponse(
  token: string,
  username: string,
  redirectUrl: string,
): Response {
  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Login Successful - Rocket CLI</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0d1117; color: #c9d1d9; }
    .container { text-align: center; padding: 40px; }
    .icon { font-size: 64px; margin-bottom: 20px; }
    h1 { color: #3fb950; }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">🚀</div>
    <h1>Welcome, ${escapeHtml(username)}!</h1>
    <p>Redirecting...</p>
  </div>
  <script>
    // Store token securely
    localStorage.setItem('rocket_session', '${token}');
    // Redirect
    window.location.href = '${redirectUrl}';
  </script>
</body>
</html>`;

  return new Response(html, {
    status: 200,
    headers: { "Content-Type": "text/html" },
  });
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
