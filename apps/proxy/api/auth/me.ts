/**
 * GET /api/auth/me
 * DELETE /api/auth/me (logout)
 *
 * Get current user info or logout.
 */

import { validateRequest, deleteSession } from "../../lib/auth";

export const config = {
  runtime: "edge",
};

interface MeResponse {
  authenticated: boolean;
  user?: {
    id: string;
    username: string;
    name: string | null;
    email: string | null;
    avatar_url: string;
  };
  session?: {
    created_at: string;
    expires_at: string;
  };
}

export default async function handler(request: Request): Promise<Response> {
  // Handle CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(),
    });
  }

  // DELETE = logout
  if (request.method === "DELETE") {
    return handleLogout(request);
  }

  // GET = get user info
  if (request.method === "GET") {
    return handleGetUser(request);
  }

  return jsonResponse({ error: "Method not allowed" }, 405);
}

async function handleGetUser(request: Request): Promise<Response> {
  const { authenticated, session } = await validateRequest(request);

  if (!authenticated || !session) {
    const response: MeResponse = { authenticated: false };
    return jsonResponse(response, 200);
  }

  const response: MeResponse = {
    authenticated: true,
    user: {
      id: session.userId,
      username: session.username,
      name: session.name,
      email: session.email,
      avatar_url: session.avatarUrl,
    },
    session: {
      created_at: new Date(session.createdAt).toISOString(),
      expires_at: new Date(session.expiresAt).toISOString(),
    },
  };

  return jsonResponse(response, 200);
}

async function handleLogout(request: Request): Promise<Response> {
  const authHeader = request.headers.get("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return jsonResponse({ error: "Not authenticated" }, 401);
  }

  const token = authHeader.slice(7);

  try {
    await deleteSession(token);
    return jsonResponse({ message: "Logged out successfully" }, 200);
  } catch (error) {
    console.error("Logout error:", error);
    return jsonResponse({ error: "Logout failed" }, 500);
  }
}

function corsHeaders(): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
}

function jsonResponse(data: unknown, status: number): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...corsHeaders(),
    },
  });
}
