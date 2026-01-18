import { NextRequest, NextResponse } from "next/server";
import { Redis } from "@upstash/redis";
import { getTodayMetrics } from "../../../../proxy/lib/analytics";

export async function GET(request: NextRequest) {
  try {
    // Get today's metrics from the analytics module
    const metrics = await getTodayMetrics();

    return NextResponse.json(metrics);
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    return NextResponse.json(
      {
        totalRequests: 0,
        totalTokens: 0,
        estimatedCost: 0,
        requestsByTier: { anonymous: 0, authenticated: 0 },
        topUsers: [],
      },
      { status: 500 },
    );
  }
}
