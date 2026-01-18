/**
 * Analytics Module
 * 
 * Tracks usage metrics to Redis and sends alerts when budget is exceeded.
 * Optionally integrates with PostHog for detailed analytics.
 */

import { Redis } from '@upstash/redis';

export interface UsageMetrics {
  totalRequests: number;
  totalTokens: number;
  estimatedCost: number;
  requestsByTier: {
    anonymous: number;
    authenticated: number;
  };
  topUsers: Array<{ id: string; requests: number }>;
}

export interface RequestLog {
  timestamp: number;
  userId: string;
  tier: 'anonymous' | 'authenticated';
  tokens: number;
  cost: number;
  model: string;
  keyUsed: string;
}

// Pricing (Gemini 1.5 Flash as of 2024)
const PRICING = {
  inputTokensPer1M: 0.075,  // $0.075 per 1M input tokens
  outputTokensPer1M: 0.30,  // $0.30 per 1M output tokens
  // Simplified: average cost per token
  avgCostPer1KTokens: 0.0001875, // ~$0.1875 per 1M tokens
};

// Redis client (lazy init)
let redis: Redis | null = null;

function getRedis(): Redis {
  if (!redis) {
    const url = process.env.UPSTASH_REDIS_REST_URL;
    const token = process.env.UPSTASH_REDIS_REST_TOKEN;

    if (!url || !token) {
      throw new Error('Missing Upstash Redis configuration');
    }

    redis = new Redis({ url, token });
  }
  return redis;
}

/**
 * Get today's date key for Redis
 */
function getTodayKey(): string {
  const now = new Date();
  return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}-${String(now.getUTCDate()).padStart(2, '0')}`;
}

/**
 * Calculate estimated cost from token count
 */
export function calculateCost(tokens: number): number {
  return (tokens / 1000) * PRICING.avgCostPer1KTokens;
}

/**
 * Track a request in analytics
 */
export async function trackRequest(log: RequestLog): Promise<void> {
  const redisClient = getRedis();
  const dateKey = getTodayKey();
  const prefix = `rocket:analytics:${dateKey}`;

  try {
    // Use pipeline for atomic operations
    const pipeline = redisClient.pipeline();

    // Increment total requests
    pipeline.incr(`${prefix}:requests`);

    // Add tokens
    pipeline.incrby(`${prefix}:tokens`, log.tokens);

    // Add cost (stored as integer cents * 1000 for precision)
    pipeline.incrby(`${prefix}:cost`, Math.round(log.cost * 100000));

    // Increment tier counter
    pipeline.incr(`${prefix}:tier:${log.tier}`);

    // Track per-user requests (for top users)
    pipeline.zincrby(`${prefix}:users`, 1, log.userId);

    // Track per-key usage
    pipeline.incr(`${prefix}:key:${log.keyUsed}`);

    // Set expiry on all keys (7 days retention)
    const expiry = 7 * 24 * 60 * 60;
    pipeline.expire(`${prefix}:requests`, expiry);
    pipeline.expire(`${prefix}:tokens`, expiry);
    pipeline.expire(`${prefix}:cost`, expiry);
    pipeline.expire(`${prefix}:tier:${log.tier}`, expiry);
    pipeline.expire(`${prefix}:users`, expiry);
    pipeline.expire(`${prefix}:key:${log.keyUsed}`, expiry);

    await pipeline.exec();

    // Check budget and alert if needed
    await checkBudgetAndAlert();

    // Optional: Send to PostHog
    await sendToPostHog(log);
  } catch (error) {
    console.error('Failed to track analytics:', error);
    // Don't throw - analytics failure shouldn't break the request
  }
}

/**
 * Get today's usage metrics
 */
export async function getTodayMetrics(): Promise<UsageMetrics> {
  const redisClient = getRedis();
  const dateKey = getTodayKey();
  const prefix = `rocket:analytics:${dateKey}`;

  try {
    const [
      requests,
      tokens,
      costRaw,
      anonRequests,
      authRequests,
      topUsersRaw,
    ] = await Promise.all([
      redisClient.get<number>(`${prefix}:requests`),
      redisClient.get<number>(`${prefix}:tokens`),
      redisClient.get<number>(`${prefix}:cost`),
      redisClient.get<number>(`${prefix}:tier:anonymous`),
      redisClient.get<number>(`${prefix}:tier:authenticated`),
      redisClient.zrange(`${prefix}:users`, 0, 9, { rev: true, withScores: true }),
    ]);

    // Parse top users
    const topUsers: Array<{ id: string; requests: number }> = [];
    if (topUsersRaw && Array.isArray(topUsersRaw)) {
      for (let i = 0; i < topUsersRaw.length; i += 2) {
        topUsers.push({
          id: String(topUsersRaw[i]),
          requests: Number(topUsersRaw[i + 1]),
        });
      }
    }

    return {
      totalRequests: requests ?? 0,
      totalTokens: tokens ?? 0,
      estimatedCost: (costRaw ?? 0) / 100000, // Convert back from stored format
      requestsByTier: {
        anonymous: anonRequests ?? 0,
        authenticated: authRequests ?? 0,
      },
      topUsers,
    };
  } catch (error) {
    console.error('Failed to get metrics:', error);
    return {
      totalRequests: 0,
      totalTokens: 0,
      estimatedCost: 0,
      requestsByTier: { anonymous: 0, authenticated: 0 },
      topUsers: [],
    };
  }
}

/**
 * Check if daily budget exceeded and send alert
 */
async function checkBudgetAndAlert(): Promise<void> {
  const budgetCap = parseFloat(process.env.DAILY_BUDGET_CAP ?? '10');
  const metrics = await getTodayMetrics();

  if (metrics.estimatedCost >= budgetCap) {
    await sendSlackAlert(
      `🚨 Rocket CLI Proxy Budget Alert!\n` +
      `Daily budget of $${budgetCap} has been exceeded.\n` +
      `Current spend: $${metrics.estimatedCost.toFixed(4)}\n` +
      `Total requests: ${metrics.totalRequests}\n` +
      `Total tokens: ${metrics.totalTokens}`
    );
  } else if (metrics.estimatedCost >= budgetCap * 0.8) {
    // Warn at 80%
    await sendSlackAlert(
      `⚠️ Rocket CLI Proxy Budget Warning\n` +
      `Daily spend at 80% of budget.\n` +
      `Current: $${metrics.estimatedCost.toFixed(4)} / $${budgetCap}`
    );
  }
}

/**
 * Send alert to Slack webhook
 */
async function sendSlackAlert(message: string): Promise<void> {
  const webhookUrl = process.env.SLACK_WEBHOOK_URL;
  if (!webhookUrl) return;

  // Deduplicate alerts (only send once per hour)
  const redisClient = getRedis();
  const alertKey = `rocket:alert:${getTodayKey()}:${Buffer.from(message).toString('base64').slice(0, 20)}`;
  
  const exists = await redisClient.get(alertKey);
  if (exists) return;

  try {
    await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: message }),
    });

    // Mark as sent (expire in 1 hour)
    await redisClient.set(alertKey, '1', { ex: 3600 });
  } catch (error) {
    console.error('Failed to send Slack alert:', error);
  }
}

/**
 * Send event to PostHog (optional)
 */
async function sendToPostHog(log: RequestLog): Promise<void> {
  const apiKey = process.env.POSTHOG_API_KEY;
  if (!apiKey) return;

  try {
    await fetch('https://app.posthog.com/capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: apiKey,
        event: 'api_request',
        distinct_id: log.userId,
        properties: {
          tier: log.tier,
          tokens: log.tokens,
          cost: log.cost,
          model: log.model,
          timestamp: log.timestamp,
        },
      }),
    });
  } catch (error) {
    // Silently fail - PostHog is optional
    console.debug('PostHog tracking failed:', error);
  }
}

/**
 * Get usage metrics for a specific date
 */
export async function getMetricsForDate(date: string): Promise<UsageMetrics> {
  const redisClient = getRedis();
  const prefix = `rocket:analytics:${date}`;

  try {
    const [requests, tokens, costRaw, anonRequests, authRequests] = await Promise.all([
      redisClient.get<number>(`${prefix}:requests`),
      redisClient.get<number>(`${prefix}:tokens`),
      redisClient.get<number>(`${prefix}:cost`),
      redisClient.get<number>(`${prefix}:tier:anonymous`),
      redisClient.get<number>(`${prefix}:tier:authenticated`),
    ]);

    return {
      totalRequests: requests ?? 0,
      totalTokens: tokens ?? 0,
      estimatedCost: (costRaw ?? 0) / 100000,
      requestsByTier: {
        anonymous: anonRequests ?? 0,
        authenticated: authRequests ?? 0,
      },
      topUsers: [],
    };
  } catch (error) {
    console.error('Failed to get metrics for date:', error);
    return {
      totalRequests: 0,
      totalTokens: 0,
      estimatedCost: 0,
      requestsByTier: { anonymous: 0, authenticated: 0 },
      topUsers: [],
    };
  }
}
