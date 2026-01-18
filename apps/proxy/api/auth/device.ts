/**
 * POST /api/auth/device
 * POST /api/auth/device/poll
 *
 * GitHub Device Flow for CLI authentication.
 * This allows authentication without a browser redirect.
 */

import {
  startDeviceFlow,
  pollDeviceToken,
  createSession,
} from "../../lib/auth";

export const config = {
  runtime: "edge",
};

interface DeviceStartResponse {
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
  device_code: string;
}

interface DevicePollRequest {
  device_code: string;
}

interface DevicePollResponse {
  status: "pending" | "success" | "expired" | "error";
  token?: string;
  user?: {
    username: string;
    name: string | null;
  };
  error?: string;
}

export default async function handler(request: Request): Promise<Response> {
  const url = new URL(request.url);

  // Handle CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(),
    });
  }

  // Route based on path
  if (url.pathname.endsWith("/device/poll")) {
    return handlePoll(request);
  }

  return handleStart(request);
}

/**
 * Start device flow - returns user code for user to enter on GitHub
 */
async function handleStart(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  try {
    const deviceCode = await startDeviceFlow();

    const response: DeviceStartResponse = {
      user_code: deviceCode.user_code,
      verification_uri: deviceCode.verification_uri,
      expires_in: deviceCode.expires_in,
      interval: deviceCode.interval,
      device_code: deviceCode.device_code,
    };

    return jsonResponse(response, 200);
  } catch (error) {
    console.error("Device flow start error:", error);
    return jsonResponse(
      {
        error:
          error instanceof Error
            ? error.message
            : "Failed to start device flow",
      },
      500,
    );
  }
}

/**
 * Poll for device flow completion
 */
async function handlePoll(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  try {
    const body = (await request.json()) as DevicePollRequest;

    if (!body.device_code) {
      return jsonResponse({ error: "Missing device_code" }, 400);
    }

    const result = await pollDeviceToken(body.device_code);

    if (result.status === "success" && result.token) {
      // Create session with the token
      const { sessionToken, session } = await createSession(result.token);

      const response: DevicePollResponse = {
        status: "success",
        token: sessionToken,
        user: {
          username: session.username,
          name: session.name,
        },
      };

      return jsonResponse(response, 200);
    }

    const response: DevicePollResponse = {
      status: result.status,
      error: result.error,
    };

    return jsonResponse(response, 200);
  } catch (error) {
    console.error("Device flow poll error:", error);
    return jsonResponse(
      { error: error instanceof Error ? error.message : "Poll failed" },
      500,
    );
  }
}

function corsHeaders(): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
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
