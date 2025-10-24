import { useState, useEffect } from 'react';
import { Database, Search, ChevronDown, ChevronRight, Loader2, AlertCircle, FileText } from 'lucide-react';
import { API_CONFIG } from '../config/api';

interface EntitySchema {
  pk: string;
  fields: string[];
}

interface OntologyData {
  [entityName: string]: EntitySchema;
}

export default function OntologyPage() {
  const [ontologyData, setOntologyData] = useState<OntologyData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEntities, setExpandedEntities] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchOntologySchema();
  }, []);

  const fetchOntologySchema = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(API_CONFIG.buildDclUrl('/ontology_schema'));
      if (!response.ok) {
        throw new Error(`Failed to fetch ontology schema: ${response.statusText}`);
      }
      const data = await response.json();
      setOntologyData(data);
    } catch (err) {
      console.error('Error fetching ontology schema:', err);
      setError(err instanceof Error ? err.message : 'Failed to load ontology schema');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleEntityExpansion = (entityName: string) => {
    setExpandedEntities(prev => {
      const newSet = new Set(prev);
      if (newSet.has(entityName)) {
        newSet.delete(entityName);
      } else {
        newSet.add(entityName);
      }
      return newSet;
    });
  };

  const filteredEntities = ontologyData
    ? Object.entries(ontologyData).filter(([entityName]) =>
        entityName.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  return (
    <div className="space-y-6">
      <div className="px-6 py-4 space-y-1">
        <h1 className="text-2xl font-semibold text-white">Ontology Schema</h1>
        <p className="text-sm text-gray-400">
          Define the canonical entities and their structure for unified data mapping
        </p>
      </div>

      <div className="px-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search entities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
          />
        </div>
      </div>

      <div className="px-6">
        {isLoading && (
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-12 text-center">
            <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
            <p className="text-gray-400">Loading ontology schema...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <p className="text-red-400 font-semibold mb-2">Error Loading Schema</p>
            <p className="text-gray-400 text-sm">{error}</p>
            <button
              onClick={fetchOntologySchema}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && ontologyData && (
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-900/50 border-b border-gray-700">
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                      Entity Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                      Primary Key
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                      Fields
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {filteredEntities.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-12 text-center">
                        <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                        <p className="text-gray-400">
                          {searchQuery ? 'No entities match your search' : 'No entities defined in ontology'}
                        </p>
                      </td>
                    </tr>
                  ) : (
                    filteredEntities.map(([entityName, schema]) => {
                      const isExpanded = expandedEntities.has(entityName);
                      return (
                        <tr key={entityName} className="hover:bg-gray-700/30 transition-colors">
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <Database className="w-4 h-4 text-blue-400 flex-shrink-0" />
                              <span className="font-semibold text-white">{entityName}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <code className="px-2 py-1 bg-gray-900/50 border border-gray-600 rounded text-sm text-cyan-400">
                              {schema.pk}
                            </code>
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-900/30 border border-purple-500/30 text-purple-400">
                              {schema.fields.length} {schema.fields.length === 1 ? 'field' : 'fields'}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() => toggleEntityExpansion(entityName)}
                              className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-lg text-sm text-gray-300 transition-colors"
                            >
                              {isExpanded ? (
                                <>
                                  <ChevronDown className="w-4 h-4" />
                                  Collapse
                                </>
                              ) : (
                                <>
                                  <ChevronRight className="w-4 h-4" />
                                  Expand
                                </>
                              )}
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {filteredEntities.map(([entityName, schema]) => {
              const isExpanded = expandedEntities.has(entityName);
              if (!isExpanded) return null;
              
              return (
                <div
                  key={`${entityName}-details`}
                  className="border-t border-gray-700 bg-gray-900/30 px-6 py-4"
                >
                  <h4 className="text-sm font-semibold text-gray-400 mb-3">
                    Fields for <span className="text-white">{entityName}</span>:
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {schema.fields.map((field) => (
                      <code
                        key={field}
                        className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm text-gray-300"
                      >
                        {field}
                      </code>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!isLoading && !error && ontologyData && filteredEntities.length > 0 && (
          <div className="mt-4 flex items-center justify-between text-sm text-gray-400">
            <span>
              Showing {filteredEntities.length} of {Object.keys(ontologyData).length} {Object.keys(ontologyData).length === 1 ? 'entity' : 'entities'}
            </span>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-blue-400 hover:text-blue-300 transition-colors"
              >
                Clear search
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
