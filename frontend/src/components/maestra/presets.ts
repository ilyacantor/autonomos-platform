/**
 * Maestra preset suggestions — config-driven, per module context.
 *
 * To add or change presets, edit this file. No component code changes needed.
 */

const MAESTRA_PRESETS: Record<string, string[]> = {
  nlq: [
    'What data do we have for Meridian?',
    'Walk me through the top COFA conflicts',
    'How is the compensation structure organized?',
    'What systems were discovered?',
  ],
  aam: [
    'What does mapping mean?',
    "What's been mapped so far?",
    'What systems are connected?',
    'How do the data flows work?',
  ],
  dcl: [
    "What's the merge status?",
    'Show me top conflicts by dollar impact',
    'How many triples are in the store?',
    'What domains have data?',
  ],
  aod: [
    'What systems were discovered?',
    'How many systems are connected?',
    'What types of systems exist?',
    "What's still pending?",
  ],
  farm: [
    'Where do the financial numbers come from?',
    "What's the difference between Meridian and Cascadia?",
    'What compensation data exists?',
    'How is revenue structured?',
  ],
  convergence: [
    'How do the two charts of accounts compare?',
    'What are the biggest conflicts by dollar impact?',
    "What's in the Diligence Integration Package?",
    'Where are the cross-sell opportunities?',
  ],
};

export default MAESTRA_PRESETS;
