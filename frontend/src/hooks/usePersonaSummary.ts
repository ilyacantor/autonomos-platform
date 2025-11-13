import { useState, useEffect } from 'react';
import type { PersonaSlug, PersonaSummaryResponse } from '../types/persona';

function getDemoData(slug: PersonaSlug): PersonaSummaryResponse {
  const demoData: Record<PersonaSlug, PersonaSummaryResponse> = {
    cto: {
      persona: 'cto',
      tiles: [
        {
          key: 'data_sources',
          title: 'Connected Sources',
          value: '3',
          delta: '+1',
          timeframe: 'Last 30 days',
          last_updated: new Date().toISOString(),
          href: '/connect',
          mock: true
        },
        {
          key: 'api_uptime',
          title: 'API Uptime',
          value: '99.8%',
          delta: '+0.2%',
          timeframe: 'Last 7 days',
          last_updated: new Date().toISOString(),
          href: '/orchestration',
          mock: true
        },
        {
          key: 'data_quality',
          title: 'Data Quality Score',
          value: '94%',
          delta: '+3%',
          timeframe: 'Current',
          last_updated: new Date().toISOString(),
          href: '/ontology',
          mock: true
        }
      ],
      table: {
        title: 'Recent System Events',
        columns: ['Event', 'Source', 'Status', 'Time'],
        rows: [
          ['Schema sync', 'Salesforce', 'Success', '2m ago'],
          ['Data ingestion', 'MongoDB', 'Success', '15m ago'],
          ['Field mapping', 'FilesSource', 'Success', '1h ago']
        ],
        href: '/orchestration',
        mock: true
      },
      trace_id: 'demo-cto-' + Date.now()
    },
    cro: {
      persona: 'cro',
      tiles: [
        {
          key: 'revenue',
          title: 'Monthly Recurring Revenue',
          value: '$124K',
          delta: '+12%',
          timeframe: 'vs last month',
          last_updated: new Date().toISOString(),
          href: '/agents',
          mock: true
        },
        {
          key: 'pipeline',
          title: 'Sales Pipeline',
          value: '$2.4M',
          delta: '+18%',
          timeframe: 'Q1 2025',
          last_updated: new Date().toISOString(),
          href: '/agents',
          mock: true
        },
        {
          key: 'conversion',
          title: 'Lead Conversion',
          value: '23%',
          delta: '+5%',
          timeframe: 'Last 30 days',
          last_updated: new Date().toISOString(),
          href: '/agents',
          mock: true
        }
      ],
      table: {
        title: 'Top Opportunities',
        columns: ['Account', 'Stage', 'Value', 'Close Date'],
        rows: [
          ['Acme Corp', 'Negotiation', '$450K', 'Mar 15'],
          ['TechStart Inc', 'Proposal', '$280K', 'Mar 22'],
          ['Global Systems', 'Discovery', '$620K', 'Apr 5']
        ],
        href: '/agents',
        mock: true
      },
      trace_id: 'demo-cro-' + Date.now()
    },
    coo: {
      persona: 'coo',
      tiles: [
        {
          key: 'efficiency',
          title: 'Operational Efficiency',
          value: '87%',
          delta: '+4%',
          timeframe: 'vs last quarter',
          last_updated: new Date().toISOString(),
          href: '/orchestration',
          mock: true
        },
        {
          key: 'automation',
          title: 'Process Automation',
          value: '72%',
          delta: '+8%',
          timeframe: 'Last 60 days',
          last_updated: new Date().toISOString(),
          href: '/orchestration',
          mock: true
        },
        {
          key: 'incidents',
          title: 'Open Incidents',
          value: '3',
          delta: '-2',
          timeframe: 'Current',
          last_updated: new Date().toISOString(),
          href: '/orchestration',
          mock: true
        }
      ],
      table: {
        title: 'Active Workflows',
        columns: ['Workflow', 'Status', 'Executions', 'Success Rate'],
        rows: [
          ['Data Sync', 'Running', '1,247', '99.2%'],
          ['ETL Pipeline', 'Running', '843', '98.8%'],
          ['Report Gen', 'Scheduled', '156', '100%']
        ],
        href: '/orchestration',
        mock: true
      },
      trace_id: 'demo-coo-' + Date.now()
    },
    cfo: {
      persona: 'cfo',
      tiles: [
        {
          key: 'burn_rate',
          title: 'Monthly Burn Rate',
          value: '$85K',
          delta: '-3%',
          timeframe: 'vs last month',
          last_updated: new Date().toISOString(),
          href: '/agents',
          mock: true
        },
        {
          key: 'runway',
          title: 'Cash Runway',
          value: '18mo',
          delta: '+2mo',
          timeframe: 'Current',
          last_updated: new Date().toISOString(),
          href: '/agents',
          mock: true
        },
        {
          key: 'arr',
          title: 'Annual Recurring Revenue',
          value: '$1.5M',
          delta: '+24%',
          timeframe: 'YoY',
          last_updated: new Date().toISOString(),
          href: '/agents',
          mock: true
        }
      ],
      table: {
        title: 'Budget vs Actuals',
        columns: ['Category', 'Budget', 'Actual', 'Variance'],
        rows: [
          ['Engineering', '$45K', '$42K', '-7%'],
          ['Sales & Marketing', '$28K', '$31K', '+11%'],
          ['Infrastructure', '$12K', '$11K', '-8%']
        ],
        href: '/agents',
        mock: true
      },
      trace_id: 'demo-cfo-' + Date.now()
    }
  };

  return demoData[slug];
}

export function usePersonaSummary(slug: PersonaSlug) {
  const [data, setData] = useState<PersonaSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchSummary() {
      setLoading(true);
      setError(null);
      
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`/nlp/v1/persona/summary?persona=${slug}`, {
          method: 'GET',
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`API unavailable`);
        }

        const result = await response.json();
        
        if (mounted) {
          setData(result);
        }
      } catch (err) {
        if (mounted) {
          setData(getDemoData(slug));
          setError(null);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    fetchSummary();

    return () => {
      mounted = false;
    };
  }, [slug]);

  return { data, loading, error };
}
