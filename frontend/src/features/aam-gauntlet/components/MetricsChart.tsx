import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import type { MetricsSummary } from '../types';

interface MetricsChartProps {
  metrics: MetricsSummary | null;
}

export default function MetricsChart({ metrics }: MetricsChartProps) {
  if (!metrics) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <div className="text-center text-gray-400">Loading metrics...</div>
      </div>
    );
  }

  const statusData = Object.entries(metrics.by_status || {}).map(([status, count]) => ({
    name: `HTTP ${status}`,
    count: count as number,
  }));

  const errorData = Object.entries(metrics.error_breakdown || {}).map(([error, count]) => ({
    name: error,
    count: count as number,
  }));

  const serviceData = Object.entries(metrics.by_service || {}).map(([service, stats]) => ({
    name: service.replace('_mock', ''),
    success: stats.success,
    errors: stats.errors,
    total: stats.total,
  }));

  const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#ec4899'];

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-3">
          <div className="text-2xl font-bold text-cyan-400">{metrics.total_requests || 0}</div>
          <div className="text-xs text-gray-400">Total Requests</div>
        </div>
        <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-3">
          <div className="text-2xl font-bold text-green-400">{metrics.successful_requests || 0}</div>
          <div className="text-xs text-gray-400">Successful</div>
        </div>
        <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-3">
          <div className="text-2xl font-bold text-red-400">{metrics.failed_requests || 0}</div>
          <div className="text-xs text-gray-400">Failed</div>
        </div>
        <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-3">
          <div className="text-2xl font-bold text-yellow-400">
            {metrics.avg_latency_ms ? `${Math.round(metrics.avg_latency_ms)}ms` : '0ms'}
          </div>
          <div className="text-xs text-gray-400">Avg Latency</div>
        </div>
      </div>

      {statusData.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2 text-gray-300">Status Code Distribution</h4>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" tick={{ fontSize: 10 }} />
              <YAxis stroke="#9ca3af" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Bar dataKey="count" fill="#06b6d4" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {errorData.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2 text-gray-300">Error Types</h4>
          <ResponsiveContainer width="100%" height={150}>
            <PieChart>
              <Pie
                data={errorData}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={50}
                fill="#8884d8"
                dataKey="count"
                label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
              >
                {errorData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                labelStyle={{ color: '#9ca3af' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {serviceData.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-2 text-gray-300">Service Performance</h4>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={serviceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" tick={{ fontSize: 10 }} />
              <YAxis stroke="#9ca3af" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: 'none' }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Bar dataKey="success" stackId="a" fill="#10b981" />
              <Bar dataKey="errors" stackId="a" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {metrics.dlq_stats && (
        <div>
          <h4 className="text-sm font-semibold mb-2 text-gray-300">Dead Letter Queue</h4>
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-2 text-center">
              <div className="text-lg font-bold text-yellow-400">{metrics.dlq_stats.pending || 0}</div>
              <div className="text-xs text-gray-400">Pending</div>
            </div>
            <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-2 text-center">
              <div className="text-lg font-bold text-green-400">{metrics.dlq_stats.processed || 0}</div>
              <div className="text-xs text-gray-400">Processed</div>
            </div>
            <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-2 text-center">
              <div className="text-lg font-bold text-red-400">{metrics.dlq_stats.failed || 0}</div>
              <div className="text-xs text-gray-400">Failed</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
