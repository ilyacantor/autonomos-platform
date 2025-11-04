import { useState, useEffect } from 'react';
import { Database, Search, ChevronDown, ChevronRight, Loader2, AlertCircle, FileText, Table, Layers, FolderTree } from 'lucide-react';
import { API_CONFIG } from '../config/api';

interface FieldMapping {
  source_field: string;
  ontology_field: string;
  confidence: number;
  transform: string;
  sql_expression: string;
}

interface SourceMapping {
  source_system: string;
  source_table: string;
  source_fields: string[];
  field_count: number;
  field_mappings?: FieldMapping[];  // Detailed field-level mappings
}

interface EntitySchema {
  pk: string;
  fields: string[];
  source_mappings: SourceMapping[];
}

interface OntologyData {
  [entityName: string]: EntitySchema;
}

interface DataSourceUniverse {
  [dataSource: string]: {
    [tableName: string]: string[];
  };
}

export default function OntologyPage() {
  const [ontologyData, setOntologyData] = useState<OntologyData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEntities, setExpandedEntities] = useState<Set<string>>(new Set());
  const [expandedDataSources, setExpandedDataSources] = useState<Set<string>>(new Set());
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'entities' | 'universe'>('entities');

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

  const toggleDataSourceExpansion = (dataSource: string) => {
    setExpandedDataSources(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dataSource)) {
        newSet.delete(dataSource);
      } else {
        newSet.add(dataSource);
      }
      return newSet;
    });
  };

  const toggleTableExpansion = (tableKey: string) => {
    setExpandedTables(prev => {
      const newSet = new Set(prev);
      if (newSet.has(tableKey)) {
        newSet.delete(tableKey);
      } else {
        newSet.add(tableKey);
      }
      return newSet;
    });
  };

  // Build the data source universe from ontology data
  const buildDataSourceUniverse = (): DataSourceUniverse => {
    const universe: DataSourceUniverse = {};
    
    if (!ontologyData) return universe;
    
    // Collect all unique combinations of data source + table + fields
    Object.values(ontologyData).forEach(schema => {
      schema.source_mappings.forEach(mapping => {
        const { source_system, source_table, source_fields } = mapping;
        
        if (!universe[source_system]) {
          universe[source_system] = {};
        }
        
        if (!universe[source_system][source_table]) {
          universe[source_system][source_table] = [];
        }
        
        // Add fields that aren't already in the list
        source_fields.forEach(field => {
          if (!universe[source_system][source_table].includes(field)) {
            universe[source_system][source_table].push(field);
          }
        });
      });
    });
    
    return universe;
  };

  const dataSourceUniverse = buildDataSourceUniverse();

  const filteredEntities = ontologyData
    ? Object.entries(ontologyData).filter(([entityName]) =>
        entityName.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  const filteredDataSources = Object.entries(dataSourceUniverse).filter(([dataSource]) =>
    dataSource.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="px-6 py-4 space-y-1">
        <h1 className="text-2xl font-medium text-white">Ontology Schema</h1>
        <p className="text-sm text-gray-400">
          Define the canonical entities and their structure for unified data mapping
        </p>
      </div>

      {/* View Mode Tabs */}
      <div className="px-6">
        <div className="flex gap-2 border-b border-gray-700">
          <button
            onClick={() => setViewMode('entities')}
            className={`px-4 py-2 font-medium text-sm transition-colors border-b-2 ${
              viewMode === 'entities'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Unified Entities View
            </div>
          </button>
          <button
            onClick={() => setViewMode('universe')}
            className={`px-4 py-2 font-medium text-sm transition-colors border-b-2 ${
              viewMode === 'universe'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            <div className="flex items-center gap-2">
              <FolderTree className="w-4 h-4" />
              Data Source Universe (Raw Materials)
            </div>
          </button>
        </div>
      </div>

      <div className="px-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder={viewMode === 'entities' ? "Search entities..." : "Search data sources..."}
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

        {/* Entities View */}
        {!isLoading && !error && ontologyData && viewMode === 'entities' && (
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-900/50 border-b border-gray-700">
                    <th className="px-6 py-3 text-left text-xs text-gray-400 tracking-wider">
                      Entity Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs text-gray-400 tracking-wider">
                      Primary Key
                    </th>
                    <th className="px-6 py-3 text-left text-xs text-gray-400 tracking-wider">
                      Unified Fields
                    </th>
                    <th className="px-6 py-3 text-left text-xs text-gray-400 tracking-wider">
                      Data Sources
                    </th>
                    <th className="px-6 py-3 text-left text-xs text-gray-400 tracking-wider">
                      Source Tables
                    </th>
                    <th className="px-6 py-3 text-left text-xs text-gray-400 tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {filteredEntities.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center">
                        <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                        <p className="text-gray-400">
                          {searchQuery ? 'No entities match your search' : 'No entities defined in ontology'}
                        </p>
                      </td>
                    </tr>
                  ) : (
                    filteredEntities.map(([entityName, schema]) => {
                      const isExpanded = expandedEntities.has(entityName);
                      const sourceSystems = [...new Set(schema.source_mappings.map(sm => sm.source_system))];
                      const sourceTables = schema.source_mappings.map(sm => `${sm.source_system}/${sm.source_table}`);
                      
                      return (
                        <tr key={entityName} className="hover:bg-gray-700/30 transition-colors">
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <Database className="w-4 h-4 text-blue-400 flex-shrink-0" />
                              <span className="text-white">{entityName}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <code className="px-2 py-1 bg-gray-900/50 border border-gray-600 rounded text-sm text-cyan-400">
                              {schema.pk}
                            </code>
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs bg-purple-900/30 border border-purple-500/30 text-purple-400">
                              {schema.fields.length} {schema.fields.length === 1 ? 'field' : 'fields'}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            {sourceSystems.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {sourceSystems.map(source => (
                                  <span key={source} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-900/30 border border-green-500/30 text-green-400">
                                    {source}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-gray-500 text-sm">No sources</span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            {sourceTables.length > 0 ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs bg-blue-900/30 border border-blue-500/30 text-blue-400">
                                {sourceTables.length} {sourceTables.length === 1 ? 'table' : 'tables'}
                              </span>
                            ) : (
                              <span className="text-gray-500 text-sm">No tables</span>
                            )}
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
                  className="border-t border-gray-700 bg-gray-900/30 px-6 py-4 space-y-4"
                >
                  {/* Unified Fields */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-3">
                      Unified Fields for <span className="text-white">{entityName}</span>:
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

                  {/* Source Mappings */}
                  {schema.source_mappings.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-3">
                        Source Mappings (Field-Level Details):
                      </h4>
                      <div className="space-y-3">
                        {schema.source_mappings.map((mapping, idx) => (
                          <div
                            key={idx}
                            className="bg-gray-800/50 border border-gray-600 rounded-lg overflow-hidden"
                          >
                            {/* Mapping Header */}
                            <div className="flex items-center gap-2 p-4 bg-gray-900/30">
                              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-900/30 border border-green-500/30 text-green-400">
                                {mapping.source_system}
                              </span>
                              <span className="text-gray-400">/</span>
                              <code className="px-2 py-1 bg-gray-900/50 border border-gray-600 rounded text-xs text-blue-400">
                                {mapping.source_table}
                              </code>
                              <span className="text-gray-500 text-xs ml-auto">
                                {mapping.field_count} {mapping.field_count === 1 ? 'field mapping' : 'field mappings'}
                              </span>
                            </div>

                            {/* Detailed Field Mappings */}
                            {mapping.field_mappings && mapping.field_mappings.length > 0 ? (
                              <div className="p-4 space-y-2">
                                {mapping.field_mappings.map((fm, fmIdx) => (
                                  <div
                                    key={fmIdx}
                                    className="flex items-center gap-3 p-3 bg-gray-900/50 border border-gray-700 rounded-lg hover:bg-gray-700/30 transition-colors"
                                  >
                                    {/* Source Field */}
                                    <code className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm text-gray-300 font-mono">
                                      {fm.source_field}
                                    </code>
                                    
                                    {/* Arrow */}
                                    <span className="text-gray-500 font-bold">→</span>
                                    
                                    {/* Ontology Field */}
                                    <code className="px-3 py-1.5 bg-blue-900/30 border border-blue-500/30 rounded text-sm text-blue-400 font-mono">
                                      {fm.ontology_field}
                                    </code>
                                    
                                    {/* Confidence Badge */}
                                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                                      fm.confidence >= 0.9 
                                        ? 'bg-green-900/30 border border-green-500/30 text-green-400' 
                                        : fm.confidence >= 0.7 
                                        ? 'bg-yellow-900/30 border border-yellow-500/30 text-yellow-400'
                                        : 'bg-orange-900/30 border border-orange-500/30 text-orange-400'
                                    }`}>
                                      {(fm.confidence * 100).toFixed(0)}% confident
                                    </span>
                                    
                                    {/* Transform Badge */}
                                    {fm.transform && fm.transform !== 'direct' && (
                                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-purple-900/30 border border-purple-500/30 text-purple-400">
                                        {fm.transform}
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              /* Fallback to old display if detailed mappings not available */
                              mapping.source_fields.length > 0 && (
                                <div className="p-4 flex flex-wrap gap-1">
                                  {mapping.source_fields.map((field, fieldIdx) => (
                                    <code
                                      key={fieldIdx}
                                      className="px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs text-gray-400"
                                    >
                                      {field}
                                    </code>
                                  ))}
                                </div>
                              )
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Data Source Universe View */}
        {!isLoading && !error && ontologyData && viewMode === 'universe' && (
          <div className="space-y-4">
            {filteredDataSources.length === 0 ? (
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-12 text-center">
                <FolderTree className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">
                  {searchQuery ? 'No data sources match your search' : 'No data sources available'}
                </p>
              </div>
            ) : (
              filteredDataSources.map(([dataSource, tables]) => {
                const isDataSourceExpanded = expandedDataSources.has(dataSource);
                const tableCount = Object.keys(tables).length;
                const totalFields = Object.values(tables).reduce((sum, fields) => sum + fields.length, 0);
                
                return (
                  <div key={dataSource} className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
                    {/* Data Source Header */}
                    <div
                      onClick={() => toggleDataSourceExpansion(dataSource)}
                      className="px-6 py-4 bg-gray-900/30 hover:bg-gray-900/50 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {isDataSourceExpanded ? (
                            <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
                          ) : (
                            <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                          )}
                          <Database className="w-5 h-5 text-green-400 flex-shrink-0" />
                          <h3 className="text-lg font-medium text-white">{dataSource}</h3>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-blue-900/30 border border-blue-500/30 text-blue-400">
                            {tableCount} {tableCount === 1 ? 'table' : 'tables'}
                          </span>
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-purple-900/30 border border-purple-500/30 text-purple-400">
                            {totalFields} {totalFields === 1 ? 'field' : 'fields'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Tables List */}
                    {isDataSourceExpanded && (
                      <div className="px-6 py-4 space-y-3">
                        {Object.entries(tables).map(([tableName, fields]) => {
                          const tableKey = `${dataSource}__${tableName}`;
                          const isTableExpanded = expandedTables.has(tableKey);
                          
                          return (
                            <div key={tableKey} className="bg-gray-900/30 border border-gray-600 rounded-lg overflow-hidden">
                              {/* Table Header */}
                              <div
                                onClick={() => toggleTableExpansion(tableKey)}
                                className="px-4 py-3 hover:bg-gray-700/30 cursor-pointer transition-colors"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    {isTableExpanded ? (
                                      <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                    ) : (
                                      <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                    )}
                                    <Table className="w-4 h-4 text-blue-400 flex-shrink-0" />
                                    <code className="text-sm font-medium text-blue-400">{tableName}</code>
                                  </div>
                                  <span className="text-xs text-gray-500">
                                    {fields.length} {fields.length === 1 ? 'field' : 'fields'}
                                  </span>
                                </div>
                              </div>

                              {/* Fields List */}
                              {isTableExpanded && (
                                <div className="px-4 py-3 border-t border-gray-700 bg-gray-800/50">
                                  <div className="flex flex-wrap gap-2">
                                    {fields.sort().map((field, idx) => (
                                      <code
                                        key={idx}
                                        className="px-3 py-1.5 bg-gray-900 border border-gray-600 rounded text-xs text-gray-300"
                                      >
                                        {field}
                                      </code>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {!isLoading && !error && ontologyData && (
          <div className="mt-4 flex items-center justify-between text-sm text-gray-400">
            <span>
              {viewMode === 'entities' ? (
                <>Showing {filteredEntities.length} of {Object.keys(ontologyData).length} {Object.keys(ontologyData).length === 1 ? 'entity' : 'entities'}</>
              ) : (
                <>Showing {filteredDataSources.length} of {Object.keys(dataSourceUniverse).length} {Object.keys(dataSourceUniverse).length === 1 ? 'data source' : 'data sources'}</>
              )}
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
