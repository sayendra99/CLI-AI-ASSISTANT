/**
 * POST /api/v1/generate
 *
 * Main generation endpoint for Rocket CLI proxy.
 * Handles rate limiting, key rotation, and Gemini API forwarding.
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import { generateWithRotation } from "../../lib/key-rotation";
import { trackRequest, calculateCost } from "../../lib/analytics";

// Rate limiter configs
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

interface GenerateRequest {
  prompt: string;
  temperature?: number;
  maxTokens?: number;
  model?: string;
}

interface GenerateResponse {
  text: string;
  model: string;
  usage: {
    remaining: number;
    limit: number;
    reset: number;
  };
}

interface ErrorResponse {
  error: string;
  code: string;
  retryAfter?: number;
}

// Vercel Edge Function config
export const config = {
  runtime: "edge",
};

export default async function handler(request: Request): Promise<Response> {
  // Only allow POST
  if (request.method !== "POST") {
    return jsonResponse(
      { error: "Method not allowed", code: "METHOD_NOT_ALLOWED" },
      405,
    );
  }

  // Parse request body
  let body: GenerateRequest;
  try {
    body = (await request.json()) as GenerateRequest;
  } catch {
    return jsonResponse(
      { error: "Invalid JSON body", code: "INVALID_JSON" },
      400,
    );
  }

  // Validate required fields
  if (!body.prompt || typeof body.prompt !== "string") {
    return jsonResponse(
      { error: "Missing or invalid prompt", code: "INVALID_PROMPT" },
      400,
    );
  }

  if (body.prompt.length > 32000) {
    return jsonResponse(
      { error: "Prompt too long (max 32000 chars)", code: "PROMPT_TOO_LONG" },
      400,
    );
  }

  // Get user identifier
  const { userId, tier } = getUserIdentifier(request);

  // Check rate limit
  const ratelimit = tier === "authenticated" ? authRatelimit : anonRatelimit;
  const { success, limit, remaining, reset } = await ratelimit.limit(userId);

  if (!success) {
    return jsonResponse(
      {
        error: "Rate limit exceeded",
        code: "RATE_LIMIT_EXCEEDED",
        retryAfter: Math.ceil((reset - Date.now()) / 1000),
      },
      429,
      {
        "X-RateLimit-Limit": limit.toString(),
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": reset.toString(),
        "Retry-After": Math.ceil((reset - Date.now()) / 1000).toString(),
      },
    );
  }

  // Check daily budget
  const budgetExceeded = await checkBudgetExceeded();
  if (budgetExceeded) {
    return jsonResponse(
      {
        error: "Service temporarily unavailable due to high demand",
        code: "BUDGET_EXCEEDED",
      },
      503,
    );
  }

  // Generate response using Gemini with key rotation
  try {
    const startTime = Date.now();

    const result = await generateWithRotation({
      prompt: body.prompt,
      temperature: body.temperature,
      maxTokens: body.maxTokens,
    });

    const latency = Date.now() - startTime;

    // Estimate token count (rough: 4 chars per token)
    const estimatedTokens = Math.ceil(
      (body.prompt.length + result.text.length) / 4,
    );
    const cost = calculateCost(estimatedTokens);

    // Track analytics (non-blocking)
    trackRequest({
      timestamp: Date.now(),
      userId,
      tier,
      tokens: estimatedTokens,
      cost,
      model: result.model,
      keyUsed: result.keyUsed,
    }).catch(console.error);

    // Prepare response
    const response: GenerateResponse = {
      text: result.text,
      model: result.model,
      usage: {
        remaining: remaining - 1,
        limit,
        reset,
      },
    };

    return jsonResponse(response, 200, {
      "X-RateLimit-Limit": limit.toString(),
      "X-RateLimit-Remaining": (remaining - 1).toString(),
      "X-RateLimit-Reset": reset.toString(),
      "X-Response-Time": `${latency}ms`,
    });
  } catch (error) {
    console.error("Generation error:", error);

    // Check for specific error types
    if (error instanceof Error) {
      if (
        error.message.includes("rate limit") ||
        error.message.includes("429")
      ) {
        return jsonResponse(
          {
            error: "Upstream rate limit exceeded",
            code: "UPSTREAM_RATE_LIMIT",
          },
          503,
        );
      }
      if (error.message.includes("API key")) {
        return jsonResponse(
          { error: "Service configuration error", code: "CONFIG_ERROR" },
          503,
        );
      }
    }

    return jsonResponse(
      { error: "Failed to generate response", code: "GENERATION_FAILED" },
      500,
    );
  }
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
    // TODO: Validate GitHub token in Phase 3
    // For now, use token hash as user ID
    return {
      userId: `github:${hashString(token)}`,
      tier: "authenticated",
    };
  }

  // Check for X-GitHub-User header (set by middleware after OAuth validation)
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
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Check if daily budget has been exceeded
 */
async function checkBudgetExceeded(): Promise<boolean> {
  const budgetCap = parseFloat(process.env.DAILY_BUDGET_CAP ?? "10");

  try {
    const today = new Date().toISOString().split("T")[0];
    const costRaw = await redis.get<number>(`rocket:analytics:${today}:cost`);
    const currentCost = (costRaw ?? 0) / 100000;

    return currentCost >= budgetCap;
  } catch {
    // If we can't check, allow the request but log the error
    console.error("Failed to check budget");
    return false;
  }
}

/**
 * Create JSON response with proper headers
 */
function jsonResponse(
  data: GenerateResponse | ErrorResponse,
  status: number,
  extraHeaders?: Record<string, string>,
): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      ...extraHeaders,
    },
  });
}
