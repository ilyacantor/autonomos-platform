import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

interface FAQItem {
  question: string;
  answer: string | JSX.Element;
}

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const toggleQuestion = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const faqItems: FAQItem[] = [
    {
      question: "What is AutonomOS?",
      answer: (
        <div className="space-y-4">
          <p className="text-gray-300">
            AutonomOS is an AI-native, <strong className="text-white">enterprise-grade</strong> platform that turns your scattered company data into action.
          </p>
          <p className="text-gray-300">
            It autonomously connects to all your apps, databases, and files, learning how they fit together to create a single, unified enterprise <strong className="text-white">ontology</strong>. This allows our specialized AI agents to reason, act, and get work done.
          </p>
          
          <div className="mt-6">
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-3">The Problem</h4>
            <p className="text-gray-300">
              Most companies are data-rich but action-poor. They can't bridge the "Insight-to-Action Gap" between their data and their business goals, leading to inefficiency and inaction.
            </p>
          </div>
          
          <div className="mt-6">
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-3">Our Solution</h4>
            <p className="text-gray-300">
              AutonomOS bridges this gap. It not only unifies your data but empowers pre-built AI agents to execute complex workflows. You remain in control with Human-in-the-Loop (HITL) guardrails. We deliver a complete, <strong className="text-white">secure</strong>, and scalable solution—combining technology with the domain expertise to ensure you get results, not just another proof-of-concept (POC).
            </p>
          </div>
        </div>
      )
    },
    {
      question: "What are your security standards?",
      answer: (
        <div className="space-y-6">
          <div>
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-4">Security & Compliance Roadmap</h4>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-[#0D2F3F]">
                    <th className="border border-[#1A4D5E] px-4 py-3 text-left text-white font-medium">
                      Phase 0: Secure Core (Today)
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-3 text-left text-white font-medium">
                      Phase 1: Enterprise Readiness (0–6 Months)
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-3 text-left text-white font-medium">
                      Phase 2: Continuous Compliance (6–18 Months)
                    </th>
                  </tr>
                  <tr className="bg-[#0A2540]">
                    <th className="border border-[#1A4D5E] px-4 py-2 text-left text-[#0BCAD9] font-normal text-sm">
                      Status: Implemented
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-2 text-left text-[#0BCAD9] font-normal text-sm">
                      Goal: Pass Enterprise Security Assessments
                    </th>
                    <th className="border border-[#1A4D5E] px-4 py-2 text-left text-[#0BCAD9] font-normal text-sm">
                      Goal: Operate with Automated Trust at Scale
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Zero Data Retention Model</strong> (Ephemeral in-memory processing)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">SOC 2 Type I Certification</strong> (Fast-tracked)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">SOC 2 Type II + ISO 27001</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Robust Multi-Tenant Isolation</strong> (DB-level, tenant-scoped queries)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">3rd-Party Penetration Test</strong></span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Bring Your Own Key (BYOK)</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Zero-Trust Infrastructure</strong> (VPC, TLS 1.3, Secrets Mgmt)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Single Sign-On (SSO)</strong> (Okta, Azure AD)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Customer-Managed RBAC</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Secure API & Software Lifecycle</strong> (Pydantic validation, CI/CD scans)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Private Connectivity</strong> (AWS PrivateLink)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Regional Data Residency Controls</strong></span>
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-green-400">✓</span>
                        <span><strong className="text-white">Immutable Audit Trail</strong> (Metadata-only logging)</span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">Public Trust Portal & Incident Response Plan</strong></span>
                      </div>
                    </td>
                    <td className="border border-[#1A4D5E] px-4 py-3 text-gray-300 align-top">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-500">🔲</span>
                        <span><strong className="text-white">AI-Driven Threat Detection</strong></span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )
    },
    {
      question: "What is the Adaptive API Mesh (AAM)?",
      answer: "The Adaptive API Mesh is an intelligent connectivity layer that uses AI to automatically build, maintain, and repair connections between disparate enterprise systems. It provides self-healing integration capabilities that adapt to changes in your data sources and APIs, ensuring your workflows remain resilient and operational without manual intervention."
    },
    {
      question: "How does the Data Connectivity Layer (DCL) work?",
      answer: "The DCL is the core data intelligence engine that autonomously maps disparate data sets into a Unified Enterprise Ontology. It uses AI to understand your data semantics, create contextual relationships, and generate AI-ready data streams. The DCL feeds a Contextual RAG engine that continuously learns from your data patterns, enabling intelligent agents to make informed decisions."
    },
    {
      question: "What are Prebuilt Domain Agents?",
      answer: "Prebuilt Domain Agents are productized domain expertise packages designed for specific business functions like FinOps and RevOps. These agents leverage the AI-prepared data fabric to autonomously execute complex, end-to-end business workflows. They use advanced LLM capabilities (supporting multiple providers like Gemini and OpenAI) to reason about your data, learn from patterns, and take intelligent actions."
    },
    {
      question: "Can I customize the agents and workflows?",
      answer: "Yes, while we provide Prebuilt Domain Agents for common use cases, the platform supports custom agent deployment. You can leverage our AI-prepared data fabric and orchestration capabilities to build agents tailored to your specific business needs. The LLM service abstraction allows you to choose the best model for each task."
    }
  ];

  return (
    <div className="min-h-screen bg-[#0A1628] py-8 px-4 safe-area">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-medium text-white mb-4">
            Frequently Asked Questions
          </h1>
          <p className="text-gray-400 text-lg">
            Learn more about AutonomOS and its AI-native capabilities
          </p>
        </div>

        <div className="space-y-4">
          {faqItems.map((item, index) => (
            <div
              key={index}
              className="bg-[#0D2F3F] border border-[#1A4D5E] rounded-xl overflow-hidden"
            >
              <button
                onClick={() => toggleQuestion(index)}
                className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-[#0F3A4F] transition-colors"
              >
                <h3 className="text-lg font-medium text-white pr-4">
                  {item.question}
                </h3>
                {openIndex === index ? (
                  <ChevronUp className="w-5 h-5 text-[#0BCAD9] flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-[#0BCAD9] flex-shrink-0" />
                )}
              </button>

              {openIndex === index && (
                <div className="px-6 py-5 border-t border-[#1A4D5E] bg-[#0A2540]">
                  {typeof item.answer === 'string' ? (
                    <p className="text-gray-300 leading-relaxed">{item.answer}</p>
                  ) : (
                    item.answer
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <div className="bg-[#0D2F3F] border border-[#0BCAD9]/30 rounded-xl p-8">
            <h3 className="text-xl font-medium text-white mb-3">
              Still have questions?
            </h3>
            <p className="text-gray-400 mb-6">
              Our team is here to help you understand how AutonomOS can transform your enterprise intelligence.
            </p>
            <button className="px-6 py-3 bg-[#0BCAD9] hover:bg-[#0AA5B3] text-white rounded-lg font-medium transition-colors">
              Contact Support
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
