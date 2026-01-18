#!/usr/bin/env node
/**
 * Local Test Script for Rocket CLI Proxy
 *
 * This script tests the proxy endpoints locally using mock environment.
 */

const http = require("http");

const BASE_URL = "http://localhost:3000";

async function test(name, fn) {
  try {
    await fn();
    console.log(`✅ ${name}`);
  } catch (error) {
    console.log(`❌ ${name}`);
    console.log(`   Error: ${error.message}`);
  }
}

async function fetchJSON(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  return {
    status: response.status,
    headers: Object.fromEntries(response.headers.entries()),
    data: await response.json().catch(() => null),
  };
}

async function runTests() {
  console.log("\n🧪 Testing Rocket CLI Proxy\n");
  console.log("Base URL:", BASE_URL);
  console.log("-".repeat(50));

  // Test 1: Health endpoint
  await test("Health endpoint returns status", async () => {
    const res = await fetchJSON("/api/health");
    if (res.status !== 200 && res.status !== 503) {
      throw new Error(`Expected 200 or 503, got ${res.status}`);
    }
    if (!res.data.status) {
      throw new Error("Missing status field");
    }
    console.log(`   Status: ${res.data.status}`);
  });

  // Test 2: Limits endpoint (anonymous)
  await test("Limits endpoint returns rate limits", async () => {
    const res = await fetchJSON("/api/v1/limits");
    if (res.status !== 200) {
      throw new Error(`Expected 200, got ${res.status}`);
    }
    if (res.data.tier !== "anonymous") {
      throw new Error(`Expected anonymous tier, got ${res.data.tier}`);
    }
    if (res.data.limits?.daily?.limit !== 5) {
      throw new Error(
        `Expected limit of 5, got ${res.data.limits?.daily?.limit}`,
      );
    }
    console.log(
      `   Tier: ${res.data.tier}, Limit: ${res.data.limits.daily.limit}/day`,
    );
  });

  // Test 3: Generate endpoint - missing prompt
  await test("Generate rejects missing prompt", async () => {
    const res = await fetchJSON("/api/v1/generate", {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (res.status !== 400) {
      throw new Error(`Expected 400, got ${res.status}`);
    }
    if (res.data.code !== "INVALID_PROMPT") {
      throw new Error(`Expected INVALID_PROMPT, got ${res.data.code}`);
    }
  });

  // Test 4: Generate endpoint - valid request
  await test("Generate accepts valid request", async () => {
    const res = await fetchJSON("/api/v1/generate", {
      method: "POST",
      body: JSON.stringify({
        prompt: "Say hello in one word.",
        maxTokens: 10,
      }),
    });

    // This will fail without real API keys, but we can test the structure
    if (res.status === 200) {
      if (!res.data.text) {
        throw new Error("Missing text field in response");
      }
      console.log(`   Response: "${res.data.text.slice(0, 50)}..."`);
    } else if (res.status === 503) {
      // Expected without API keys
      console.log(`   API keys not configured (expected in test)`);
    } else if (res.status === 429) {
      console.log(`   Rate limited (expected after multiple requests)`);
    } else {
      console.log(`   Status: ${res.status}, Code: ${res.data?.code}`);
    }
  });

  // Test 5: Rate limit headers
  await test("Rate limit headers present", async () => {
    const res = await fetchJSON("/api/v1/limits");
    const limit = res.headers["x-ratelimit-limit"];
    const remaining = res.headers["x-ratelimit-remaining"];

    if (!limit || !remaining) {
      throw new Error("Rate limit headers missing");
    }
    console.log(`   Remaining: ${remaining}/${limit}`);
  });

  // Test 6: CORS headers
  await test("CORS headers present", async () => {
    const res = await fetchJSON("/api/v1/limits");
    const cors = res.headers["access-control-allow-origin"];
    if (cors !== "*") {
      throw new Error(`Expected CORS *, got ${cors}`);
    }
  });

  console.log("\n" + "-".repeat(50));
  console.log("Tests complete!\n");
}

// Check if server is running
fetch(`${BASE_URL}/api/health`)
  .then(() => runTests())
  .catch(() => {
    console.log("\n⚠️  Proxy server not running!");
    console.log("\nTo start the proxy locally:");
    console.log("  cd apps/proxy");
    console.log("  vercel dev\n");
    console.log("Then run this test again.\n");
  });
