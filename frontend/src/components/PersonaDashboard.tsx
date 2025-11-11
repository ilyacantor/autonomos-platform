import { TrendingUp, TrendingDown, AlertCircle, Loader2, BarChart3, Cable } from 'lucide-react';
import { usePersonaSummary } from '../hooks/usePersonaSummary';
import type { PersonaSlug } from '../types/persona';
import { slugToLabel, getPersonaIcon, getPersonaColor } from '../types/persona';

interface PersonaDashboardProps {
  persona: PersonaSlug;
}

export default function PersonaDashboard({ persona }: PersonaDashboardProps) {
  const { data, loading, error } = usePersonaSummary(persona);

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-12">
        <div className="flex items-center justify-center gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading {slugToLabel(persona)} dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg border border-red-700 p-6">
        <div className="flex items-center gap-3 text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Failed to load dashboard: {error}</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const colorClasses = {
    blue: 'from-blue-900 to-cyan-900',
    purple: 'from-purple-900 to-pink-900',
    green: 'from-green-900 to-emerald-900',
    amber: 'from-amber-900 to-orange-900'
  };

  const bgGradient = colorClasses[getPersonaColor(persona) as keyof typeof colorClasses] || colorClasses.blue;

  const IconComponent = getPersonaIcon(persona);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className={`bg-gradient-to-r ${bgGradient} px-6 py-4 border-b border-gray-700`}>
        <div className="flex items-center gap-3">
          <IconComponent className="w-8 h-8 text-white" />
          <div>
            <h2 className="text-xl font-semibold text-white">{slugToLabel(persona)} Dashboard</h2>
            <p className="text-sm text-gray-300">Role-specific KPIs and insights</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.tiles.map((tile) => {
            const isStub = tile.note === 'stub';
            const TileTag = isStub ? 'div' : 'a';
            
            return (
              <TileTag
                key={tile.key}
                href={!isStub ? tile.href : undefined}
                className={`block p-4 rounded-lg border transition-colors ${
                  isStub
                    ? 'bg-gray-900 border-gray-700 opacity-60 cursor-not-allowed'
                    : 'bg-gray-900 border-gray-700 hover:border-gray-600 hover:shadow-lg'
                }`}
                title={isStub ? 'Data source not connected yet' : tile.title}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-400">{tile.title}</h3>
                  {tile.delta && !isStub && (
                    <span className={`text-xs flex items-center gap-1 ${
                      tile.delta.startsWith('+') ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {tile.delta.startsWith('+') ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {tile.delta}
                    </span>
                  )}
                </div>
                <div className="text-2xl font-bold text-white mb-1">
                  {tile.value ?? <span className="text-gray-600">—</span>}
                </div>
                <div className="text-xs text-gray-500">{tile.timeframe}</div>
                {isStub && (
                  <div className="mt-2 text-xs text-amber-600 italic">Coming soon</div>
                )}
                {!isStub && tile.value === null && (
                  <div className="mt-2 text-xs text-blue-400 italic">Connecting...</div>
                )}
              </TileTag>
            );
          })}
        </div>

        <div className={`rounded-lg border p-4 ${
          data.table.note === 'stub'
            ? 'bg-gray-900 border-gray-700 opacity-60'
            : 'bg-gray-900 border-gray-700'
        }`}>
          <h3 className="text-lg font-semibold text-white mb-4">{data.table.title}</h3>
          
          {data.table.rows.length === 0 ? (
            <div className="text-center py-8">
              {data.table.note === 'stub' ? (
                <div className="text-gray-500 flex flex-col items-center gap-2">
                  <BarChart3 className="w-12 h-12 text-gray-600" />
                  <p className="text-lg mb-2">Coming Soon</p>
                  <p className="text-sm text-gray-600">This data source will be available in a future release</p>
                </div>
              ) : (
                <div className="text-gray-500 flex flex-col items-center gap-2">
                  <Cable className="w-12 h-12 text-blue-600" />
                  <p className="text-lg mb-2">No data yet</p>
                  <p className="text-sm text-blue-400">Connect your data source to see insights here</p>
                </div>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    {data.table.columns.map((col, i) => (
                      <th key={i} className="text-left p-3 text-gray-400 font-medium">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.table.rows.map((row, i) => (
                    <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                      {row.map((cell, j) => (
                        <td key={j} className="p-3 text-gray-200">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="text-xs text-gray-600 text-center">
          Trace ID: {data.trace_id}
        </div>
      </div>
    </div>
  );
}
