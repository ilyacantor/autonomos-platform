# AutonomOS Discovery Demo - Replit Designer Transfer Package

## Overview
This is a standalone UI component ready for visual design work in Replit Designer.

## Files
- `DiscoveryDemo_Standalone.tsx` - Complete self-contained component (no backend)

## Dependencies Required
```json
{
  "dependencies": {
    "react": "^18.x",
    "reactflow": "^11.x",
    "framer-motion": "^10.x",
    "lucide-react": "^0.x",
    "clsx": "^2.x",
    "tailwind-merge": "^2.x"
  }
}
```

## What's Included
✅ Complete Discovery Demo UI
✅ ReactFlow graph visualization
✅ 4-stage pipeline workflow
✅ Interactive navigation
✅ All mock data inline
✅ No backend dependencies
✅ No database dependencies

## Usage in Designer
1. Copy `DiscoveryDemo_Standalone.tsx` to Designer project
2. Install dependencies listed above
3. Import and render: `<DiscoveryDemoStandalone />`
4. Modify visuals, layouts, styling as needed
5. Export back when done

## Current Functionality
- **Run Full Pipeline**: Starts demo, pauses at each stage
- **Stage Navigation**: 4 stages (AOD → AAM → DCL → Agents)
- **Interactive Prompts**: User controls when to continue
- **Graph Animations**: Nodes light up at each stage
- **Responsive Design**: 2/3 graph, 1/3 detail panel

## What Needs Design Work
The graph visualization animations aren't working smoothly. Focus on:
- Stage lighting behavior
- Node pulse/glow effects
- Edge animations
- Overall visual polish

## Notes
- All TypeScript
- Uses Tailwind CSS
- Quicksand font family
- Dark mode theme (slate-950 background)
- Cyan/Green/Purple color scheme
