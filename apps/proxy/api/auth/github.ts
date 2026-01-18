/**
 * GET /api/auth/github
 *
 * Initiates GitHub OAuth web flow.
 * Redirects user to GitHub authorization page.
 */

import { generateState, getAuthorizationUrl, storeState } from "../../lib/auth";

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

    // Get redirect URI from query param or use default
    const redirectParam =
      url.searchParams.get("redirect") || "/api/auth/callback";
    const baseUrl = `${url.protocol}//${url.host}`;
    const callbackUrl = `${baseUrl}/api/auth/callback`;

    // Generate and store state for CSRF protection
    const state = generateState();
    await storeState(state, redirectParam);

    // Build GitHub authorization URL
    const authUrl = getAuthorizationUrl(state, callbackUrl);

    // Redirect to GitHub
    return Response.redirect(authUrl, 302);
  } catch (error) {
    console.error("GitHub OAuth init error:", error);
    return new Response(JSON.stringify({ error: "Failed to initiate OAuth" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
