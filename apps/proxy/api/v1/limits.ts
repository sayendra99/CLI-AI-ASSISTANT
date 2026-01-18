/**
 * GET /api/v1/limits
 *
 * Returns rate limit information for the requesting user.
 * Used by CLI to show remaining requests.
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

export const config = {
  runtime: "edge",
};

// Redis client
const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL!,
  token: process.env.UPSTASH_REDIS_REST_TOKEN!,
});

// Anonymous users: 5 requests per day
const anonRatelimit = new Ratelimit({
  redis,
  limiter: Ratelimit.fixedWindow(5, "1 d"),
  prefix: "rocket:ratelimit:anon",
  analytics: true,
});

// Authenticated users: 25 requests per day
const authRatelimit = new Ratelimit({
  redis,
  limiter: Ratelimit.fixedWindow(25, "1 d"),
  prefix: "rocket:ratelimit:auth",
  analytics: true,
});

interface LimitsResponse {
  tier: "anonymous" | "authenticated";
  limits: {
    daily: {
      limit: number;
      remaining: number;
      reset: number;
      resetAt: string;
    };
  };
  benefits: {
    current: string[];
    upgrade?: string[];
  };
}

export default async function handler(request: Request): Promise<Response> {
  // Handle CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      },
    });
  }

  // Only allow GET
  if (request.method !== "GET") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  // Get user identifier
  const { userId, tier } = getUserIdentifier(request);

  // Get current rate limit status (without consuming)
  const ratelimit = tier === "authenticated" ? authRatelimit : anonRatelimit;

  // Use getRemaining to check status without consuming
  const { limit, remaining, reset } = await ratelimit.getRemaining(userId);

  const response: LimitsResponse = {
    tier,
    limits: {
      daily: {
        limit,
        remaining,
        reset,
        resetAt: new Date(reset).toISOString(),
      },
    },
    benefits: {
      current:
        tier === "authenticated"
          ? [
              "25 requests per day",
              "Priority support",
              "Usage analytics",
              "Early access to new features",
            ]
          : ["5 requests per day", "Basic LLM access", "Community support"],
    },
  };

  // Show upgrade benefits for anonymous users
  if (tier === "anonymous") {
    response.benefits.upgrade = [
      "5x more daily requests (25/day)",
      "Priority support",
      "Usage analytics dashboard",
      "Early access to new features",
    ];
  }

  return jsonResponse(response, 200, {
    "X-RateLimit-Limit": limit.toString(),
    "X-RateLimit-Remaining": remaining.toString(),
    "X-RateLimit-Reset": reset.toString(),
  });
}

/**
 * Extract user identifier from request
 */
function getUserIdentifier(request: Request): {
  userId: string;
  tier: "anonymous" | "authenticated";
} {
  // Check for GitHub OAuth token
  const authHeader = request.headers.get("Authorization");
  if (authHeader?.startsWith("Bearer ")) {
    const token = authHeader.slice(7);
    return {
      userId: `github:${hashString(token)}`,
      tier: "authenticated",
    };
  }

  // Check for X-GitHub-User header
  const githubUser = request.headers.get("X-GitHub-User");
  if (githubUser) {
    return {
      userId: `github:${githubUser}`,
      tier: "authenticated",
    };
  }

  // Fall back to IP-based identification
  const forwardedFor = request.headers.get("X-Forwarded-For");
  const realIp = request.headers.get("X-Real-IP");
  const ip = forwardedFor?.split(",")[0].trim() || realIp || "unknown";

  return {
    userId: `ip:${hashString(ip)}`,
    tier: "anonymous",
  };
}

/**
 * Simple string hash for privacy
 */
function hashString(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(36);
}

/**
 * Create JSON response with proper headers
 */
function jsonResponse(
  data: LimitsResponse | { error: string },
  status: number,
  extraHeaders?: Record<string, string>,
): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-cache",
      ...extraHeaders,
    },
  });
}
