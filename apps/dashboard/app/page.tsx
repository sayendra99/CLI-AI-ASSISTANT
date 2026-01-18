import { Suspense } from "react";

interface UsageMetrics {
  totalRequests: number;
  totalTokens: number;
  estimatedCost: number;
  requestsByTier: {
    anonymous: number;
    authenticated: number;
  };
  topUsers: Array<{ id: string; requests: number }>;
}

async function getStats(): Promise<UsageMetrics> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_PROXY_URL || "http://localhost:3000"}/api/stats`,
      {
        cache: "no-store",
      },
    );
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    return {
      totalRequests: 0,
      totalTokens: 0,
      estimatedCost: 0,
      requestsByTier: { anonymous: 0, authenticated: 0 },
      topUsers: [],
    };
  }
}

function StatsCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
      {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
    </div>
  );
}

function TopUsersTable({
  users,
}: {
  users: Array<{ id: string; requests: number }>;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Top Users</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Requests
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((user, index) => (
              <tr key={user.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                  {user.id.length > 20 ? `${user.id.slice(0, 20)}...` : user.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {user.requests}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

async function DashboardContent() {
  const stats = await getStats();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Rocket CLI Analytics Dashboard
          </h1>
          <p className="text-gray-600 mt-2">
            Real-time usage statistics and monitoring
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Total Requests"
            value={stats.totalRequests.toLocaleString()}
            subtitle="Today"
          />
          <StatsCard
            title="Total Tokens"
            value={stats.totalTokens.toLocaleString()}
            subtitle="Processed today"
          />
          <StatsCard
            title="Estimated Cost"
            value={`$${stats.estimatedCost.toFixed(4)}`}
            subtitle="Daily budget"
          />
          <StatsCard
            title="Active Users"
            value={stats.topUsers.length}
            subtitle="Top contributors"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <StatsCard
            title="Anonymous Requests"
            value={stats.requestsByTier.anonymous}
            subtitle="IP-based users"
          />
          <StatsCard
            title="Authenticated Requests"
            value={stats.requestsByTier.authenticated}
            subtitle="GitHub users"
          />
        </div>

        <TopUsersTable users={stats.topUsers} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-gray-600 mt-4">Loading dashboard...</p>
          </div>
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
