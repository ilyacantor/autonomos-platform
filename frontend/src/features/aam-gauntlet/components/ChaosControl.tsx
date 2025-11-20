import { useState } from 'react';
import { Zap, CloudLightning, Flame, Play, RotateCcw } from 'lucide-react';
import { gauntletClient } from '../api/gauntletClient';

interface ChaosControlProps {
  onScenarioRun: (scenario: any) => void;
}

export default function ChaosControl({ onScenarioRun }: ChaosControlProps) {
  const [chaosLevel, setChaosLevel] = useState('mild');
  const [duration, setDuration] = useState(30);
  const [selectedServices, setSelectedServices] = useState<string[]>([
    'salesforce_mock',
    'mongodb_mock',
    'stripe_mock'
  ]);
  const [isRunning, setIsRunning] = useState(false);

  const services = [
    'salesforce_mock',
    'mongodb_mock',
    'supabase_mock',
    'stripe_mock',
    'github_mock',
    'datadog_mock'
  ];

  const handleRunScenario = async () => {
    setIsRunning(true);
    try {
      await gauntletClient.setChaosLevel(chaosLevel);
      
      const scenario = {
        mode: chaosLevel as 'mild' | 'storm' | 'hell',
        duration_seconds: duration,
        connectors: selectedServices
      };
      
      const result = await gauntletClient.runScenario(scenario);
      onScenarioRun(result);
    } catch (error) {
      console.error('Failed to run scenario:', error);
    } finally {
      setIsRunning(false);
    }
  };

  const handleReset = async () => {
    try {
      await gauntletClient.resetFarmMetrics();
      await gauntletClient.setChaosLevel('mild');
      setChaosLevel('mild');
    } catch (error) {
      console.error('Failed to reset:', error);
    }
  };

  const getChaosIcon = () => {
    switch (chaosLevel) {
      case 'mild':
        return <Zap className="text-green-400" size={20} />;
      case 'storm':
        return <CloudLightning className="text-yellow-400" size={20} />;
      case 'hell':
        return <Flame className="text-red-400" size={20} />;
      default:
        return <Zap className="text-gray-400" size={20} />;
    }
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
      <h2 className="text-xl font-bold mb-4 text-gray-300 flex items-center">
        {getChaosIcon()}
        <span className="ml-2">Chaos Control Panel</span>
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Chaos Level
          </label>
          <div className="space-y-2">
            {['mild', 'storm', 'hell'].map(level => (
              <label key={level} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  value={level}
                  checked={chaosLevel === level}
                  onChange={(e) => setChaosLevel(e.target.value)}
                  className="text-cyan-500"
                  disabled={isRunning}
                />
                <span className={`capitalize ${
                  level === 'mild' ? 'text-green-400' :
                  level === 'storm' ? 'text-yellow-400' :
                  'text-red-400'
                }`}>
                  {level}
                </span>
                <span className="text-xs text-gray-500">
                  {level === 'mild' && '(5% errors)'}
                  {level === 'storm' && '(20% errors)'}
                  {level === 'hell' && '(50% errors)'}
                </span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Duration (seconds)
          </label>
          <input
            type="range"
            min="10"
            max="120"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="w-full"
            disabled={isRunning}
          />
          <div className="text-center text-lg font-bold text-cyan-400">{duration}s</div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Target Services
          </label>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {services.map(service => (
              <label key={service} className="flex items-center space-x-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedServices.includes(service)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedServices([...selectedServices, service]);
                    } else {
                      setSelectedServices(selectedServices.filter(s => s !== service));
                    }
                  }}
                  className="text-cyan-500"
                  disabled={isRunning}
                />
                <span className="text-gray-300">{service.replace('_mock', '')}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex flex-col justify-end space-y-2">
          <button
            onClick={handleRunScenario}
            disabled={isRunning || selectedServices.length === 0}
            className={`px-4 py-2 rounded font-medium flex items-center justify-center space-x-2 transition-colors ${
              isRunning || selectedServices.length === 0
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-cyan-600 text-white hover:bg-cyan-700'
            }`}
          >
            <Play size={16} />
            <span>{isRunning ? 'Running...' : 'Run Scenario'}</span>
          </button>
          <button
            onClick={handleReset}
            disabled={isRunning}
            className="px-4 py-2 rounded font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors flex items-center justify-center space-x-2"
          >
            <RotateCcw size={16} />
            <span>Reset</span>
          </button>
        </div>
      </div>

      <div className="mt-4 p-3 bg-gray-700/50 border border-gray-600 rounded-lg">
        <div className="text-sm text-gray-300">
          <strong>Current Mode: </strong>
          <span className={`capitalize ${
            chaosLevel === 'mild' ? 'text-green-400' :
            chaosLevel === 'storm' ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {chaosLevel}
          </span>
        </div>
        <div className="text-xs text-gray-400 mt-1">
          {chaosLevel === 'mild' && 'Minimal errors, normal rate limits, stable network'}
          {chaosLevel === 'storm' && 'Moderate errors, aggressive rate limits, network flakiness'}
          {chaosLevel === 'hell' && 'High error rate, severe rate limiting, frequent timeouts'}
        </div>
      </div>
    </div>
  );
}
