import { ArrowRight, ArrowDown, Database, Network, Layers, Users, TrendingUp, MousePointerClick } from 'lucide-react';
import autonomosArrow from '../assets/autonomos-arrow.png';

const SnowflakeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" className="w-12 h-12">
    <path d="M142.8 51.9l17.4-10.1 1.8 4.6c2.1 5.5 7.8 8.7 13.6 7.7l6.5-1.1-7.5 37.5-17.5 10.1-14.3-48.7zM121 197.6l-17.4 10.1-1.8-4.6c-2.1-5.5-7.8-8.7-13.6-7.7l-6.5 1.1 7.5-37.5 17.5-10.1 14.3 48.7zM170.6 64.6l11.4-18.5 4.2 2.6c4.9 3 11.3 2.1 15.2-2.1l4.4-4.8 3 37.7-11.4 18.5-26.8-33.4zM93.2 184.9l-11.4 18.5-4.2-2.6c-4.9-3-11.3-2.1-15.2 2.1l-4.4 4.8-3-37.7 11.4-18.5 26.8 33.4zM191.9 88.9l3.8-20 5.4.5c6.3.6 11.9-3.8 13.3-10.4l1.6-7.4 14.1 35.9-3.8 20-34.4-18.6zM71.9 160.6l-3.8 20-5.4-.5c-6.3-.6-11.9 3.8-13.3 10.4l-1.6 7.4-14.1-35.9 3.8-20 34.4 18.6zM206.3 118.5l-4.9-19.7 5.3-1.3c6.2-1.5 10.1-7.6 9.3-14.4l-.9-7.7 20 33.6 4.9 19.7-33.7-10.2zM57.5 130.9l4.9 19.7-5.3 1.3c-6.2 1.5-10.1 7.6-9.3 14.4l.9 7.7-20-33.6-4.9-19.7 33.7 10.2zM209.3 152.3l-9-17.9 4.7-2.9c5.5-3.4 7.4-10.5 4.5-16.7l-3.3-6.9 22.1 30.8 9 17.9-28.1-4.3zM54.5 97.2l9 17.9-4.7 2.9c-5.5 3.4-7.4 10.5-4.5 16.7l3.3 6.9-22.1-30.8-9-17.9 28.1 4.3zM198.7 180.5l-12.9-16.2 3.9-3.9c4.6-4.5 4.9-11.8.8-17.1l-4.6-5.9 22.7 27.9 12.9 16.2-22.8-1zM64.9 68.9l12.9 16.2-3.9 3.9c-4.6 4.5-4.9 11.8-.8 17.1l4.6 5.9-22.7-27.9-12.9-16.2 22.8 1zM175.6 200.9l-15.9-13.2 2.8-4.6c3.3-5.3 2.1-12.2-2.8-16.2l-5.5-4.5 21.3 24.2 15.9 13.2-15.8 1.1zM87.8 48.5l15.9 13.2-2.8 4.6c-3.3 5.3-2.1 12.2 2.8 16.2l5.5 4.5-21.3-24.2-15.9-13.2 15.8-1.1z"/>
    <path d="M132 74.3l-4.5 23.8-21.1 12.3-21.1-12.3-4.5-23.8L96.5 59l21.1-12.3L138.7 59l-6.7 15.3zM132 181.7l-4.5-23.8-21.1-12.3-21.1 12.3-4.5 23.8 15.7 15.3 21.1 12.3 21.1-12.3-6.7-15.3zM176.8 106.2l-23.8-4.5L140.7 85l4.5-23.8 15.3-6.7 15.3 6.7 12.3 21.1-6.7 15.3-4.6 8.6zM87 143.8l23.8 4.5L123.1 171l-4.5 23.8-15.3 6.7-15.3-6.7-12.3-21.1 6.7-15.3 4.6-8.6zM178.9 141.7l-23.8 4.5-8.6-4.6-8.6-15.3 8.6-15.3 8.6-4.6 23.8 4.5 15.3 15.3-15.3 15.5zM84.9 107.3l23.8-4.5 8.6 4.6 8.6 15.3-8.6 15.3-8.6 4.6-23.8-4.5-15.3-15.3 15.3-15.5z"/>
  </svg>
);

const AutonomOSArchitectureFlow = () => {
  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const modules = [
    {
      icon: Database,
      title: 'Enterprise Data',
      tags: ['SaaS Applications', 'Databases & Warehouses', 'Legacy Systems', 'APIs & Files'],
      bgColor: 'bg-[#0A2540]',
      borderColor: 'border-[#1E4A6F]',
      linkTo: null
    },
    {
      icon: Network,
      title: 'Adaptive API Mesh (AAM)',
      tags: ['Self-Healing Integration', 'Autonomous Drift Repair', 'Real-time Schema Normalization', 'Universal Connectivity', 'Governed Data Exchange'],
      bgColor: 'bg-[#0D2F3F]',
      borderColor: 'border-[#1A4D5E]',
      linkTo: 'adaptive-api-mesh'
    },
    {
      icon: Layers,
      title: 'Data Connectivity Layer',
      tags: ['Unified Enterprise Ontology', 'Semantic Context Engine', 'AI-Ready Data Streams', 'Contextual RAG Indexing', 'Real-time Observability'],
      bgColor: 'bg-[#1A2F4A]',
      borderColor: 'border-[#2A4A6F]',
      linkTo: 'dcl-graph-container'
    },
    {
      icon: Users,
      title: 'Prebuilt Domain Agents',
      tags: ['Productized Domain Expertise', 'FinOps/RevOps Blueprints', 'Autonomous Workflow Orchestration', 'Custom Agent Deployment', 'Business Process and Integration Support'],
      bgColor: 'bg-[#2A1F4A]',
      borderColor: 'border-[#3F2F6F]',
      linkTo: 'agent-performance-monitor'
    }
  ];

  return (
    <div className="w-full bg-[#0A1628] py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <div className="inline-block bg-[#0D3A52] text-[#0BCAD9] px-4 py-2 rounded-lg text-sm font-medium mb-4 border border-[#0BCAD9]/30">
            Agentic Orchestration Architecture (AOA)
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-6 bg-gradient-to-br from-[#0BCAD9]/5 via-transparent to-[#0BCAD9]/5 rounded-3xl border-2 border-[#0BCAD9]/20 pointer-events-none">
            <div className="absolute -top-3 left-8 bg-[#0A1628] px-3 py-1 text-[#0BCAD9] text-sm font-medium">
              AutonomOS Orchestration Platform
            </div>
          </div>

          <div className="relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {modules.map((module, index) => (
                <div key={index} className="relative flex flex-col items-center">
                  <div
                    onClick={() => module.linkTo && scrollToSection(module.linkTo)}
                    className={`${module.bgColor} ${module.borderColor} border-2 rounded-xl p-5 w-full hover:border-[#0BCAD9] transition-all duration-300 ${module.linkTo ? 'cursor-pointer' : ''}`}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <module.icon className="w-6 h-6 text-[#0BCAD9]" />
                      <h3 className="text-white font-medium text-base leading-tight">
                        {module.title}
                      </h3>
                      {index === 2 && (
                        <div className="flex items-center gap-1.5 ml-auto">
                          <MousePointerClick className="w-5 h-5 text-[#0BCAD9]" />
                          <span className="text-xs text-[#0BCAD9] font-medium">Interactive Demo</span>
                        </div>
                      )}
                    </div>

                    {/* Enterprise Data icons */}
                    {index === 0 && (
                      <div className="flex items-center justify-center gap-4 mb-4 py-3">
                        <div 
                          className="text-[#29B5E8] opacity-80 hover:opacity-100 transition-opacity"
                          style={{ filter: 'drop-shadow(0 0 8px rgba(41, 181, 232, 0.4))' }}
                        >
                          <SnowflakeIcon />
                        </div>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-1.5">
                      {module.tags.map((tag, tagIndex) => (
                        <span
                          key={tagIndex}
                          className="text-xs px-2 py-1 rounded bg-[#0BCAD9]/10 text-[#0BCAD9] border border-[#0BCAD9]/30"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Arrows showing flow: Data → AAM → DCL → Agents */}
                  <>
                    {/* Desktop (4-column): Horizontal arrows between all boxes */}
                    {index < modules.length - 1 && (
                      <div className="hidden lg:flex absolute top-1/2 -right-7 transform -translate-y-1/2 z-20">
                        <div className="bg-[#0BCAD9] rounded-full p-2 shadow-lg shadow-[#0BCAD9]/50">
                          <ArrowRight className="w-7 h-7 text-[#0A1628] font-bold" strokeWidth={3} />
                        </div>
                      </div>
                    )}
                    
                    {/* Tablet (2-column grid): Data → AAM → DCL → Agents */}
                    {/* 0→1: Data → AAM (horizontal in row 1) */}
                    {index === 0 && (
                      <div className="hidden md:flex lg:hidden absolute top-1/2 -right-7 transform -translate-y-1/2 z-20">
                        <div className="bg-[#0BCAD9] rounded-full p-2 shadow-lg shadow-[#0BCAD9]/50">
                          <ArrowRight className="w-7 h-7 text-[#0A1628] font-bold" strokeWidth={3} />
                        </div>
                      </div>
                    )}
                    
                    {/* 1→2: AAM → DCL (vertical between rows) */}
                    {index === 1 && (
                      <div className="hidden md:flex lg:hidden justify-center py-4">
                        <div className="bg-[#0BCAD9] rounded-full p-2 shadow-lg shadow-[#0BCAD9]/50">
                          <ArrowDown className="w-7 h-7 text-[#0A1628] font-bold" strokeWidth={3} />
                        </div>
                      </div>
                    )}
                    
                    {/* 2→3: DCL → Agents (horizontal in row 2) */}
                    {index === 2 && (
                      <div className="hidden md:flex lg:hidden absolute top-1/2 -right-7 transform -translate-y-1/2 z-20">
                        <div className="bg-[#0BCAD9] rounded-full p-2 shadow-lg shadow-[#0BCAD9]/50">
                          <ArrowRight className="w-7 h-7 text-[#0A1628] font-bold" strokeWidth={3} />
                        </div>
                      </div>
                    )}
                    
                    {/* Mobile (1-column): Vertical arrows between all boxes */}
                    {index < modules.length - 1 && (
                      <div className="flex md:hidden justify-center py-4">
                        <div className="bg-[#0BCAD9] rounded-full p-2 shadow-lg shadow-[#0BCAD9]/50 animate-pulse">
                          <ArrowDown className="w-7 h-7 text-[#0A1628] font-bold" strokeWidth={3} />
                        </div>
                      </div>
                    )}
                  </>
                </div>
              ))}
            </div>

            {/* Summary Arrow Transition - Semi-transparent AutonomOS logo */}
            <div className="flex justify-center py-8">
              <img 
                src={autonomosArrow} 
                alt="Summary transition" 
                className="w-32 md:w-48 h-auto opacity-30 hover:opacity-50 transition-opacity duration-300"
              />
            </div>

            <div className="flex justify-center">
              <div className="flex items-center gap-3 bg-[#0D2F3F] rounded-xl px-6 py-3 border border-[#0BCAD9]/30">
                <TrendingUp className="w-5 h-5 text-[#0BCAD9]" />
                <span className="text-white font-medium">Outcomes</span>
                <div className="flex flex-wrap gap-1.5 ml-2">
                  {['Intent-Driven Operations', 'Autonomous Execution', 'Insight-to-Action Acceleration', 'Guaranteed Data Reliability', 'Proactive Decision Intelligence'].map((tag, index) => (
                    <span
                      key={index}
                      className="text-xs px-2 py-1 rounded bg-[#0BCAD9]/10 text-[#0BCAD9] border border-[#0BCAD9]/30"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AutonomOSArchitectureFlow;
