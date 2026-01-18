/**
 * Rate Limiting Module
 *
 * Uses Upstash Redis for distributed rate limiting.
 * Supports two tiers:
 * - Anonymous (by IP): 5 requests/day
 * - Authenticated (GitHub): 25 requests/day
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

// Rate limit configurations
export const RATE_LIMITS = {
  anonymous: {
    requests: 5,
    window: "1 d", // 1 day
    identifier: "anon",
  },
  authenticated: {
    requests: 25,
    window: "1 d",
    identifier: "auth",
  },
} as const;

export type RateLimitTier = keyof typeof RATE_LIMITS;

export interface RateLimitResult {
  success: boolean;
  limit: number;
  remaining: number;
  reset: number; // Unix timestamp
  tier: RateLimitTier;
}

// Lazy initialization of Redis client
let redis: Redis | null = null;
let rateLimiters: Record<RateLimitTier, Ratelimit> | null = null;

/**
 * Get or create Redis client
 */
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
 * Get or create rate limiters
 */
function getRateLimiters(): Record<RateLimitTier, Ratelimit> {
  if (!rateLimiters) {
    const redisClient = getRedis();

    rateLimiters = {
      anonymous: new Ratelimit({
        redis: redisClient,
        limiter: Ratelimit.slidingWindow(
          RATE_LIMITS.anonymous.requests,
          RATE_LIMITS.anonymous.window,
        ),
        prefix: "rocket:ratelimit:anon",
        analytics: true,
      }),
      authenticated: new Ratelimit({
        redis: redisClient,
        limiter: Ratelimit.slidingWindow(
          RATE_LIMITS.authenticated.requests,
          RATE_LIMITS.authenticated.window,
        ),
        prefix: "rocket:ratelimit:auth",
        analytics: true,
      }),
    };
  }
  return rateLimiters;
}

/**
 * Check rate limit for a given identifier
 *
 * @param identifier - IP address or GitHub user ID
 * @param tier - Rate limit tier (anonymous or authenticated)
 * @returns Rate limit result with remaining requests
 */
export async function checkRateLimit(
  identifier: string,
  tier: RateLimitTier = "anonymous",
): Promise<RateLimitResult> {
  const limiters = getRateLimiters();
  const limiter = limiters[tier];
  const config = RATE_LIMITS[tier];

  const result = await limiter.limit(identifier);

  // Calculate reset time (end of current day UTC)
  const now = new Date();
  const resetDate = new Date(now);
  resetDate.setUTCHours(24, 0, 0, 0);
  const reset = Math.floor(resetDate.getTime() / 1000);

  return {
    success: result.success,
    limit: config.requests,
    remaining: result.remaining,
    reset,
    tier,
  };
}

/**
 * Get current rate limit status without consuming a request
 *
 * @param identifier - IP address or GitHub user ID
 * @param tier - Rate limit tier
 * @returns Current rate limit status
 */
export async function getRateLimitStatus(
  identifier: string,
  tier: RateLimitTier = "anonymous",
): Promise<RateLimitResult> {
  const redisClient = getRedis();
  const config = RATE_LIMITS[tier];
  const prefix = `rocket:ratelimit:${config.identifier}`;

  // Get current count from Redis
  // Note: This is an approximation as we're using sliding window
  const key = `${prefix}:${identifier}`;

  try {
    // Try to get the current window data
    const count = (await redisClient.get<number>(key)) || 0;
    const remaining = Math.max(0, config.requests - count);

    // Calculate reset time
    const now = new Date();
    const resetDate = new Date(now);
    resetDate.setUTCHours(24, 0, 0, 0);
    const reset = Math.floor(resetDate.getTime() / 1000);

    return {
      success: remaining > 0,
      limit: config.requests,
      remaining,
      reset,
      tier,
    };
  } catch {
    // If we can't get status, return full limit
    const now = new Date();
    const resetDate = new Date(now);
    resetDate.setUTCHours(24, 0, 0, 0);

    return {
      success: true,
      limit: config.requests,
      remaining: config.requests,
      reset: Math.floor(resetDate.getTime() / 1000),
      tier,
    };
  }
}

/**
 * Extract client IP from request headers
 */
export function getClientIP(headers: Headers): string {
  // Check various headers for real IP (Vercel, Cloudflare, etc.)
  const forwardedFor = headers.get("x-forwarded-for");
  if (forwardedFor) {
    return forwardedFor.split(",")[0].trim();
  }

  const realIP = headers.get("x-real-ip");
  if (realIP) {
    return realIP;
  }

  const vercelIP = headers.get("x-vercel-forwarded-for");
  if (vercelIP) {
    return vercelIP.split(",")[0].trim();
  }

  // Fallback
  return "unknown";
}

/**
 * Extract GitHub user from Authorization header
 * Returns null if not authenticated or invalid token
 */
export async function getGitHubUser(
  authHeader: string | null,
): Promise<{ id: string; username: string } | null> {
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return null;
  }

  const token = authHeader.slice(7);

  try {
    // Validate token with GitHub API
    const response = await fetch("https://api.github.com/user", {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github.v3+json",
        "User-Agent": "rocket-cli-proxy",
      },
    });

    if (!response.ok) {
      return null;
    }

    const user = (await response.json()) as { id: number; login: string };
    return {
      id: String(user.id),
      username: user.login,
    };
  } catch {
    return null;
  }
}
