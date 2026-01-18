/**
 * API Key Rotation Module
 *
 * Rotates between multiple Gemini API keys to:
 * 1. Distribute load across keys
 * 2. Handle individual key rate limits
 * 3. Provide failover if one key is exhausted
 */

import { GoogleGenerativeAI } from "@google/generative-ai";

export interface GeminiKey {
  key: string;
  name: string;
  isHealthy: boolean;
  lastError: string | null;
  lastUsed: Date | null;
  requestCount: number;
}

export interface GenerateRequest {
  prompt: string;
  systemInstruction?: string;
  temperature?: number;
  maxTokens?: number;
}

export interface GenerateResult {
  text: string;
  model: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  keyUsed: string;
}

// In-memory key state (resets on cold start, but that's fine for Vercel)
const keyStates: Map<string, GeminiKey> = new Map();

/**
 * Get all configured Gemini API keys
 */
function getConfiguredKeys(): GeminiKey[] {
  const keys: GeminiKey[] = [];

  // Primary key (required)
  const primary = process.env.GEMINI_KEY_PRIMARY;
  if (primary) {
    keys.push(getOrCreateKeyState("primary", primary));
  }

  // Fallback keys (optional)
  const fallback1 = process.env.GEMINI_KEY_FALLBACK_1;
  if (fallback1) {
    keys.push(getOrCreateKeyState("fallback1", fallback1));
  }

  const fallback2 = process.env.GEMINI_KEY_FALLBACK_2;
  if (fallback2) {
    keys.push(getOrCreateKeyState("fallback2", fallback2));
  }

  return keys;
}

/**
 * Get or create key state
 */
function getOrCreateKeyState(name: string, key: string): GeminiKey {
  if (!keyStates.has(name)) {
    keyStates.set(name, {
      key,
      name,
      isHealthy: true,
      lastError: null,
      lastUsed: null,
      requestCount: 0,
    });
  }
  return keyStates.get(name)!;
}

/**
 * Select the best key to use based on:
 * 1. Health status
 * 2. Load balancing (least recently used)
 */
export function selectKey(): GeminiKey | null {
  const keys = getConfiguredKeys();

  if (keys.length === 0) {
    return null;
  }

  // Filter to healthy keys
  const healthyKeys = keys.filter((k) => k.isHealthy);

  if (healthyKeys.length === 0) {
    // All keys unhealthy, try the one with oldest error (might have recovered)
    const oldestError = keys.sort((a, b) => {
      if (!a.lastUsed) return -1;
      if (!b.lastUsed) return 1;
      return a.lastUsed.getTime() - b.lastUsed.getTime();
    })[0];

    // Reset health to try again
    oldestError.isHealthy = true;
    return oldestError;
  }

  // Round-robin: select least recently used
  const selected = healthyKeys.sort((a, b) => {
    if (!a.lastUsed) return -1;
    if (!b.lastUsed) return 1;
    return a.lastUsed.getTime() - b.lastUsed.getTime();
  })[0];

  return selected;
}

/**
 * Mark a key as unhealthy after an error
 */
function markKeyUnhealthy(name: string, error: string): void {
  const state = keyStates.get(name);
  if (state) {
    state.isHealthy = false;
    state.lastError = error;
  }
}

/**
 * Generate content using Gemini with automatic key rotation
 */
export async function generateWithRotation(
  request: GenerateRequest,
): Promise<GenerateResult> {
  const maxRetries = 3;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const keyInfo = selectKey();

    if (!keyInfo) {
      throw new Error("No Gemini API keys configured");
    }

    try {
      const result = await generateWithKey(keyInfo, request);

      // Update key state on success
      keyInfo.lastUsed = new Date();
      keyInfo.requestCount++;
      keyInfo.isHealthy = true;
      keyInfo.lastError = null;

      return result;
    } catch (error) {
      lastError = error as Error;
      const errorMessage = lastError.message.toLowerCase();

      // Check if error is due to rate limit or quota
      if (
        errorMessage.includes("rate limit") ||
        errorMessage.includes("quota") ||
        errorMessage.includes("resource exhausted") ||
        errorMessage.includes("429")
      ) {
        console.warn(`Key ${keyInfo.name} rate limited, trying next key...`);
        markKeyUnhealthy(keyInfo.name, "Rate limited");
        continue;
      }

      // Check if error is due to invalid key
      if (
        errorMessage.includes("api key") ||
        errorMessage.includes("unauthorized") ||
        errorMessage.includes("403") ||
        errorMessage.includes("invalid")
      ) {
        console.error(`Key ${keyInfo.name} is invalid`);
        markKeyUnhealthy(keyInfo.name, "Invalid API key");
        continue;
      }

      // Other errors - don't retry with different key
      throw error;
    }
  }

  throw lastError || new Error("All API keys exhausted");
}

/**
 * Generate content with a specific key
 */
async function generateWithKey(
  keyInfo: GeminiKey,
  request: GenerateRequest,
): Promise<GenerateResult> {
  const genAI = new GoogleGenerativeAI(keyInfo.key);
  const model = genAI.getGenerativeModel({
    model: "gemini-1.5-flash",
  });

  // Build generation config
  const generationConfig = {
    temperature: request.temperature ?? 0.7,
    maxOutputTokens: request.maxTokens ?? 2048,
  };

  // Build prompt
  let fullPrompt = request.prompt;
  if (request.systemInstruction) {
    fullPrompt = `${request.systemInstruction}\n\n${request.prompt}`;
  }

  // Generate content
  const result = await model.generateContent({
    contents: [{ role: "user", parts: [{ text: fullPrompt }] }],
    generationConfig,
  });

  const response = result.response;
  const text = response.text();

  // Extract usage metadata
  const usageMetadata = response.usageMetadata;
  const usage = {
    promptTokens: usageMetadata?.promptTokenCount ?? 0,
    completionTokens: usageMetadata?.candidatesTokenCount ?? 0,
    totalTokens: usageMetadata?.totalTokenCount ?? 0,
  };

  return {
    text,
    model: "gemini-1.5-flash",
    usage,
    keyUsed: keyInfo.name,
  };
}

/**
 * Get health status of all keys
 */
export function getKeyHealth(): Array<{
  name: string;
  isHealthy: boolean;
  lastError: string | null;
  requestCount: number;
}> {
  const keys = getConfiguredKeys();
  return keys.map((k) => ({
    name: k.name,
    isHealthy: k.isHealthy,
    lastError: k.lastError,
    requestCount: k.requestCount,
  }));
}

/**
 * Check if any keys are configured
 */
export function hasConfiguredKeys(): boolean {
  return !!process.env.GEMINI_KEY_PRIMARY;
}
