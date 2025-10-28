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
            AutonomOS is an AI-native platform that connects all of your company's scattered data—from different apps, databases, and files—and makes it instantly usable. It's built with intelligence at every layer, from data connection to agent execution.
          </p>
          <p className="text-gray-300">
            It works by connecting to all your systems, autonomously learning how the data fits together, and creating a single, unified view. This allows both your team and our specialized AI agents to reason, act, and get work done.
          </p>
          
          <div className="mt-6">
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-3">The Problem We Solve</h4>
            <p className="text-gray-300">
              Most modern companies are data-rich but action-poor. They are often paralyzed by a chasm between their data, their business objectives, and their operational ability to execute. This "Insight-to-Action Gap" leads to revenue leakage, operational inefficiency, and inaction.
            </p>
          </div>
          
          <div className="mt-6">
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-3">Our Solution</h4>
            <p className="text-gray-300">
              AutonomOS is designed to bridge this gap. Our platform not only unifies your data but also uses pre-built AI agents to act on it. These agents are designed to function autonomously within the specific guardrails you establish and include escalation points for Human-in-the-Loop (HITL) approval, ensuring you are always in control.
            </p>
            <p className="text-gray-300 mt-3">
              The entire platform is built as an enterprise-grade solution, ensuring secure, scalable, and robust operations. Our goal is to lead the shift from interacting with complex legacy software to engaging directly with your data through a unified, natural language experience.
            </p>
          </div>
          
          <div className="mt-6">
            <h4 className="text-[#0BCAD9] font-medium text-lg mb-3">More Than Just Technology</h4>
            <p className="text-gray-300">
              We understand that implementing durable, effective solutions requires deep domain expertise. Our solution is never just a piece of technology; we provide the business process expertise to ensure you get a working solution, not just another proof-of-concept (POC).
            </p>
          </div>
        </div>
      )
    },
    {
      question: "How does AutonomOS use AI to power this platform?",
      answer: (
        <div className="space-y-4">
          <p className="text-gray-300">
            The demo runs on AutonomOS, our new AI-native platform. We've built intelligence into every layer, from the data fabric to the agentic execution:
          </p>
          <ul className="space-y-3 text-gray-300">
            <li>
              <strong className="text-[#0BCAD9]">AI-Driven Connectivity (AAM):</strong> Our Adaptive API Mesh uses AI to proactively build and learn connectivity between systems. This isn't just a static setup; it provides autonomous drift repair and self-healing integration to ensure workflows are resilient to the constant changes in your underlying data sources and APIs.
            </li>
            <li>
              <strong className="text-[#0BCAD9]">AI-Powered Data Layer (DCL):</strong> The Data Connectivity Layer (DCL) is the core data intelligence engine. It uses AI to autonomously map disparate data sets into a Unified Enterprise Ontology. This feeds a Contextual RAG engine that continuously learns from your data, creating AI-ready streams. This process is orchestrated by our AOA engine, using an embedded DuckDB for high-performance in-memory analytics.
            </li>
            <li>
              <strong className="text-[#0BCAD9]">Autonomous Agent Execution:</strong> Our Prebuilt Domain Agents leverage this AI-prepared data fabric to execute complex, end-to-end business workflows. The system is designed with an LLM service abstraction (supporting Gemini, OpenAI, etc.) allowing agents to use the best model for the job to reason, learn, and act.
            </li>
            <li>
              <strong className="text-[#0BCAD9]">Enterprise-Grade Foundation:</strong> This all runs on a secure, scalable multi-tenant backend. The stack is built on FastAPI (with Pydantic validation) for the API, PostgreSQL/SQLAlchemy for persistence, and Redis with Python RQ for robust, asynchronous task orchestration. This manages the entire task lifecycle, including automatic retries, timeouts, callbacks, and task chaining for complex workflows.
            </li>
            <li>
              <strong className="text-[#0BCAD9]">Secure by Design:</strong> The platform is fully multi-tenant, with complete data isolation enforced at the database level (tenant_id scoping). All authentication is handled via JWT with industry-standard Argon2 password hashing.
            </li>
          </ul>
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
      question: "Is AutonomOS secure for enterprise use?",
      answer: "Yes, AutonomOS is built with enterprise security as a core principle. The platform is fully multi-tenant with complete data isolation enforced at the database level through tenant_id scoping. All authentication uses JWT tokens with industry-standard Argon2 password hashing. The architecture ensures that each organization's data remains completely isolated and secure."
    },
    {
      question: "What technology stack powers AutonomOS?",
      answer: "AutonomOS runs on a modern, production-ready stack: FastAPI with Pydantic validation for the API layer, PostgreSQL with SQLAlchemy for data persistence, Redis with Python RQ for asynchronous task orchestration, and DuckDB for high-performance in-memory analytics. The frontend is built with React and TypeScript using Vite for optimal performance."
    },
    {
      question: "Can I customize the agents and workflows?",
      answer: "Yes, while we provide Prebuilt Domain Agents for common use cases, the platform supports custom agent deployment. You can leverage our AI-prepared data fabric and orchestration capabilities to build agents tailored to your specific business needs. The LLM service abstraction allows you to choose the best model for each task."
    },
    {
      question: "How does AutonomOS handle data from multiple sources?",
      answer: "AutonomOS uses the Adaptive API Mesh to connect to various data sources (SaaS applications, databases, warehouses, legacy systems, APIs, and files). The DCL then autonomously maps this disparate data into a Unified Enterprise Ontology, creating a semantic layer that agents can understand and act upon. This eliminates the need for manual data pipeline construction."
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
