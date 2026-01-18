/**
 * GET /api/health
 *
 * Health check endpoint for monitoring and load balancers.
 */

import { Redis } from "@upstash/redis";
import { getKeyHealth } from "../lib/key-rotation";
import { getTodayMetrics } from "../lib/analytics";

export const config = {
  runtime: "edge",
};

interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  version: string;
  components: {
    redis: "ok" | "error";
    gemini: "ok" | "degraded" | "error";
  };
  metrics?: {
    requestsToday: number;
    estimatedCostToday: number;
    healthyKeys: number;
    totalKeys: number;
  };
}

export default async function handler(request: Request): Promise<Response> {
  // Only allow GET
  if (request.method !== "GET") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json" },
    });
  }

  const health: HealthResponse = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    version: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7) ?? "dev",
    components: {
      redis: "ok",
      gemini: "ok",
    },
  };

  // Check Redis connection
  try {
    const redis = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL!,
      token: process.env.UPSTASH_REDIS_REST_TOKEN!,
    });
    await redis.ping();
    health.components.redis = "ok";
  } catch (error) {
    console.error("Redis health check failed:", error);
    health.components.redis = "error";
    health.status = "unhealthy";
  }

  // Check Gemini key health
  try {
    const keyHealth = getKeyHealth();
    const healthyKeys = keyHealth.filter((k) => k.isHealthy).length;
    const totalKeys = keyHealth.length;

    if (totalKeys === 0) {
      health.components.gemini = "error";
      health.status = "unhealthy";
    } else if (healthyKeys === 0) {
      health.components.gemini = "error";
      health.status = "unhealthy";
    } else if (healthyKeys < totalKeys) {
      health.components.gemini = "degraded";
      if (health.status === "healthy") {
        health.status = "degraded";
      }
    }

    // Include metrics if requested
    const includeMetrics =
      new URL(request.url).searchParams.get("metrics") === "true";
    if (includeMetrics) {
      const metrics = await getTodayMetrics();
      health.metrics = {
        requestsToday: metrics.totalRequests,
        estimatedCostToday: metrics.estimatedCost,
        healthyKeys,
        totalKeys,
      };
    }
  } catch (error) {
    console.error("Gemini health check failed:", error);
    health.components.gemini = "error";
    health.status = "degraded";
  }

  // Return appropriate status code
  const statusCode =
    health.status === "healthy"
      ? 200
      : health.status === "degraded"
        ? 200
        : 503;

  return new Response(JSON.stringify(health), {
    status: statusCode,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache, no-store, must-revalidate",
    },
  });
}
