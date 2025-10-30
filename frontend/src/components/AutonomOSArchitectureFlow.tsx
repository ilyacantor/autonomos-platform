import { ArrowRight, ArrowDown, Database, Network, Layers, Users, TrendingUp, MousePointerClick } from 'lucide-react';
import autonomosArrow from '../assets/autonomos-arrow.png';

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
      linkedTags: [] as string[],
      bgColor: 'bg-[#0A2540]',
      borderColor: 'border-[#1E4A6F]',
      linkTo: null
    },
    {
      icon: Network,
      title: 'Adaptive API Mesh (AAM)',
      tags: ['Self-Healing Integration', 'Autonomous Drift Repair', 'Real-time Schema Normalization', 'Universal Connectivity', 'Governed Data Exchange'],
      linkedTags: [] as string[],
      bgColor: 'bg-[#0D2F3F]',
      borderColor: 'border-[#1A4D5E]',
      linkTo: 'adaptive-api-mesh'
    },
    {
      icon: Layers,
      title: 'Data Connectivity Layer',
      tags: ['Unified Enterprise Ontology', 'Semantic Context Engine', 'AI-Ready Data Streams', 'Contextual RAG Indexing', 'Real-time Observability'],
      linkedTags: [] as string[],
      bgColor: 'bg-[#1A2F4A]',
      borderColor: 'border-[#2A4A6F]',
      linkTo: 'dcl-graph-container'
    },
    {
      icon: Users,
      title: 'Custom Domain Agents',
      tags: ['FinOps', 'RevOps', 'Productized Domain Expertise', 'FinOps/RevOps Blueprints', 'Autonomous Workflow Orchestration', 'Business Process and Integration Support', 'Insight to Action at Scale'],
      linkedTags: ['FinOps', 'RevOps'] as string[],
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

                    <div className="flex flex-wrap gap-1.5">
                      {module.tags.map((tag, tagIndex) => {
                        const isLinked = module.linkedTags.includes(tag);
                        return (
                          <span
                            key={tagIndex}
                            className={`text-xs px-2 py-1 rounded border ${
                              isLinked 
                                ? 'bg-[#0BCAD9]/20 text-white border-[#0BCAD9] font-medium shadow-lg shadow-[#0BCAD9]/30 animate-pulse' 
                                : 'bg-[#0BCAD9]/10 text-[#0BCAD9] border-[#0BCAD9]/30'
                            }`}
                          >
                            {tag}
                          </span>
                        );
                      })}
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
