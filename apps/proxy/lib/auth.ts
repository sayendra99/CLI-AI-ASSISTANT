/**
 * GitHub OAuth Authentication Module
 *
 * Handles GitHub OAuth flow for rocket-cli authentication.
 * Supports both web flow (browser redirect) and device flow (CLI).
 */

import { Redis } from "@upstash/redis";

// GitHub OAuth configuration
export const GITHUB_CONFIG = {
  clientId: process.env.GITHUB_CLIENT_ID!,
  clientSecret: process.env.GITHUB_CLIENT_SECRET!,
  // Scopes: read:user for profile info only
  scopes: ["read:user"],
  authorizationUrl: "https://github.com/login/oauth/authorize",
  tokenUrl: "https://github.com/login/oauth/access_token",
  deviceCodeUrl: "https://github.com/login/device/code",
  userUrl: "https://api.github.com/user",
};

export interface GitHubUser {
  id: number;
  login: string;
  name: string | null;
  email: string | null;
  avatar_url: string;
}

export interface AuthSession {
  userId: string;
  username: string;
  name: string | null;
  email: string | null;
  avatarUrl: string;
  accessToken: string;
  createdAt: number;
  expiresAt: number;
}

export interface DeviceCodeResponse {
  device_code: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
}

// Redis client for session storage
let redis: Redis | null = null;

function getRedis(): Redis {
  if (!redis) {
    const url = process.env.UPSTASH_REDIS_REST_URL;
    const token = process.env.UPSTASH_REDIS_REST_TOKEN;

    if (!url || !token) {
      throw new Error("Missing Upstash Redis configuration");
    }

    redis = new Redis({ url, token });
  }
  return redis;
}

/**
 * Generate a secure random state token
 */
export function generateState(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Generate authorization URL for web flow
 */
export function getAuthorizationUrl(
  state: string,
  redirectUri: string,
): string {
  const params = new URLSearchParams({
    client_id: GITHUB_CONFIG.clientId,
    redirect_uri: redirectUri,
    scope: GITHUB_CONFIG.scopes.join(" "),
    state,
    allow_signup: "true",
  });

  return `${GITHUB_CONFIG.authorizationUrl}?${params.toString()}`;
}

/**
 * Exchange authorization code for access token
 */
export async function exchangeCodeForToken(code: string): Promise<string> {
  const response = await fetch(GITHUB_CONFIG.tokenUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      client_id: GITHUB_CONFIG.clientId,
      client_secret: GITHUB_CONFIG.clientSecret,
      code,
    }),
  });

  if (!response.ok) {
    throw new Error(`GitHub token exchange failed: ${response.status}`);
  }

  const data = (await response.json()) as {
    access_token?: string;
    error?: string;
    error_description?: string;
  };

  if (data.error) {
    throw new Error(
      `GitHub OAuth error: ${data.error_description || data.error}`,
    );
  }

  if (!data.access_token) {
    throw new Error("No access token in response");
  }

  return data.access_token;
}

/**
 * Start device authorization flow (for CLI)
 */
export async function startDeviceFlow(): Promise<DeviceCodeResponse> {
  const response = await fetch(GITHUB_CONFIG.deviceCodeUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      client_id: GITHUB_CONFIG.clientId,
      scope: GITHUB_CONFIG.scopes.join(" "),
    }),
  });

  if (!response.ok) {
    throw new Error(`Device flow initiation failed: ${response.status}`);
  }

  const data = (await response.json()) as DeviceCodeResponse;
  return data;
}

/**
 * Poll for device flow token
 */
export async function pollDeviceToken(
  deviceCode: string,
): Promise<{
  status: "pending" | "success" | "expired" | "error";
  token?: string;
  error?: string;
}> {
  const response = await fetch(GITHUB_CONFIG.tokenUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      client_id: GITHUB_CONFIG.clientId,
      device_code: deviceCode,
      grant_type: "urn:ietf:params:oauth:grant-type:device_code",
    }),
  });

  const data = (await response.json()) as {
    access_token?: string;
    error?: string;
    error_description?: string;
  };

  if (data.error === "authorization_pending") {
    return { status: "pending" };
  }

  if (data.error === "slow_down") {
    return { status: "pending" };
  }

  if (data.error === "expired_token") {
    return { status: "expired" };
  }

  if (data.error) {
    return { status: "error", error: data.error_description || data.error };
  }

  if (data.access_token) {
    return { status: "success", token: data.access_token };
  }

  return { status: "error", error: "Unknown response" };
}

/**
 * Fetch GitHub user profile
 */
export async function getGitHubUser(accessToken: string): Promise<GitHubUser> {
  const response = await fetch(GITHUB_CONFIG.userUrl, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "rocket-cli-proxy",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch GitHub user: ${response.status}`);
  }

  const user = (await response.json()) as GitHubUser;
  return user;
}

/**
 * Create and store a session
 */
export async function createSession(
  accessToken: string,
): Promise<{ sessionToken: string; session: AuthSession }> {
  const user = await getGitHubUser(accessToken);

  const sessionToken = generateState(); // Use same secure random for session ID
  const now = Date.now();
  const expiresIn = 30 * 24 * 60 * 60 * 1000; // 30 days

  const session: AuthSession = {
    userId: `github:${user.id}`,
    username: user.login,
    name: user.name,
    email: user.email,
    avatarUrl: user.avatar_url,
    accessToken,
    createdAt: now,
    expiresAt: now + expiresIn,
  };

  // Store session in Redis
  const redisClient = getRedis();
  await redisClient.set(
    `rocket:session:${sessionToken}`,
    JSON.stringify(session),
    {
      ex: Math.floor(expiresIn / 1000), // TTL in seconds
    },
  );

  // Also store reverse lookup (user -> session) for logout all
  await redisClient.sadd(`rocket:user_sessions:${user.id}`, sessionToken);

  return { sessionToken, session };
}

/**
 * Validate and get session from token
 */
export async function getSession(
  sessionToken: string,
): Promise<AuthSession | null> {
  if (!sessionToken) return null;

  const redisClient = getRedis();
  const sessionData = await redisClient.get<string>(
    `rocket:session:${sessionToken}`,
  );

  if (!sessionData) return null;

  const session: AuthSession =
    typeof sessionData === "string" ? JSON.parse(sessionData) : sessionData;

  // Check if expired
  if (session.expiresAt < Date.now()) {
    await deleteSession(sessionToken);
    return null;
  }

  return session;
}

/**
 * Delete a session (logout)
 */
export async function deleteSession(sessionToken: string): Promise<void> {
  const redisClient = getRedis();

  // Get session to find user ID
  const session = await getSession(sessionToken);

  // Delete session
  await redisClient.del(`rocket:session:${sessionToken}`);

  // Remove from user's sessions
  if (session) {
    const userId = session.userId.replace("github:", "");
    await redisClient.srem(`rocket:user_sessions:${userId}`, sessionToken);
  }
}

/**
 * Validate session token from Authorization header
 */
export async function validateRequest(
  request: Request,
): Promise<{ authenticated: boolean; session?: AuthSession }> {
  const authHeader = request.headers.get("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return { authenticated: false };
  }

  const token = authHeader.slice(7);
  const session = await getSession(token);

  if (!session) {
    return { authenticated: false };
  }

  return { authenticated: true, session };
}

/**
 * Store state for CSRF protection
 */
export async function storeState(
  state: string,
  redirectUri: string,
): Promise<void> {
  const redisClient = getRedis();
  await redisClient.set(`rocket:oauth_state:${state}`, redirectUri, {
    ex: 600, // 10 minutes
  });
}

/**
 * Validate and consume state
 */
export async function validateState(state: string): Promise<string | null> {
  const redisClient = getRedis();
  const redirectUri = await redisClient.get<string>(
    `rocket:oauth_state:${state}`,
  );

  if (redirectUri) {
    await redisClient.del(`rocket:oauth_state:${state}`);
  }

  return redirectUri;
}
