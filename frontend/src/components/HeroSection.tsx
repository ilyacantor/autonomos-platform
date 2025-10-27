export default function HeroSection() {
  const scrollToDCL = () => {
    const dclElement = document.getElementById('dcl-graph-container');
    if (dclElement) {
      dclElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="px-4 sm:px-6 py-8 sm:py-12 safe-x">
      {/* Main Hero Content */}
      <div>
        <img 
          src="/assets/autonomos-logo.png" 
          alt="autonomOS" 
          className="h-12 sm:h-16 object-contain mb-4 sm:-mt-12 sm:-ml-5"
        />
        <h2 className="text-lg sm:text-xl font-medium text-white">
          The Operating System for the Intelligent Enterprise
        </h2>
        <p className="text-lg sm:text-2xl font-normal text-gray-200 max-w-3xl leading-snug mt-6 sm:mt-9 mb-6 sm:mb-[40px]">
          <span className="text-cyan-400 font-medium">autonomOS</span> connects, normalizes, maps, and orchestrates
          your enterprise data <span className="text-cyan-400 font-medium">automatically</span> — freeing
          your teams to focus on insights, not integration.
        </p>
      </div>

      {/* Value Proposition */}
      <div className="mt-4 sm:mt-6">
        <p className="text-xl sm:text-3xl font-medium leading-tight">
          <span className="text-cyan-400">Stop building pipelines.</span> <span className="text-white">Start delivering outcomes.</span>
        </p>
      </div>

      {/* Run Interactive Demo Button */}
      <div className="mt-6 sm:mt-8">
        <button
          onClick={scrollToDCL}
          className="bg-cyan-500 hover:bg-cyan-600 text-white font-medium px-6 sm:px-8 py-3 sm:py-3 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-cyan-500/50 touch-target mobile-tap-highlight text-base sm:text-base"
        >
          Run Interactive Demo
        </button>
      </div>
    </div>
  );
}
