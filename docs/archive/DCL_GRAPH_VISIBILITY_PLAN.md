# DCL Graph Maximum Visibility Plan
**Date**: October 25, 2025  
**Objective**: Ensure all DCL graph nodes are visible in the container regardless of screen size and device

---

## Current State Analysis

### Existing Implementation
**File**: `frontend/src/components/LiveSankeyGraph.tsx`

**Current Issues**:
1. **Fixed Height Constraints** (lines 200, 209)
   - Mobile: 400px, Tablet: 500px, Desktop: 600px
   - May not accommodate variable node counts (2-20+ sources)
   - Overflow clipped by clipPath, hiding nodes

2. **Static Sizing** (lines 204-205)
   - `validWidth` and `validHeight` calculated once
   - Doesn't adjust to actual content size
   - No consideration for node density

3. **90° Rotation Applied** (line 340)
   - Graph rotated for vertical flow
   - Complicates responsive calculations
   - Width/height semantics inverted

4. **No Zoom/Pan Functionality**
   - Users can't explore large graphs
   - Touch gestures not supported
   - No way to inspect dense areas

5. **ClipPath Enforcement** (lines 325-340)
   - Prevents overflow but may hide content
   - No warning when nodes are clipped

6. **Fixed Padding** (lines 235-236)
   - 20px left/right padding doesn't scale
   - May be too much on mobile, too little on desktop

---

## Proposed Solutions

### 1. **Dynamic Height Based on Node Count** [PRIORITY: HIGH]

**Goal**: Container height automatically adapts to display all nodes

**Implementation**:
```typescript
// Calculate minimum height needed for all nodes
const nodeCount = sankeyNodes.length;
const nodePadding = 18; // Current node padding
const minNodeHeight = 10; // Minimum visible height per node

// Calculate required height based on nodes in tallest layer
const nodesPerLayer = {
  source_parent: nodes.filter(n => n.type === 'source_parent').length,
  source: nodes.filter(n => n.type === 'source').length,
  ontology: nodes.filter(n => n.type === 'ontology').length,
  agent: nodes.filter(n => n.type === 'agent').length,
};

const maxNodesInLayer = Math.max(...Object.values(nodesPerLayer));
const calculatedHeight = (maxNodesInLayer * minNodeHeight) + 
                         ((maxNodesInLayer - 1) * nodePadding) + 
                         80; // Top + bottom padding

const responsiveHeight = Math.max(
  isMobile ? 400 : isTablet ? 500 : 600,  // Minimum
  calculatedHeight,                        // Content-based
  isMobile ? 600 : 1000                   // Maximum
);
```

**Benefits**:
- All nodes always visible
- Scales with content
- Respects device constraints

---

### 2. **Responsive Container Sizing** [PRIORITY: HIGH]

**Goal**: Container adapts to available viewport space

**Implementation**:
```typescript
// Use ResizeObserver for dynamic container sizing
useEffect(() => {
  if (!containerRef.current) return;
  
  const resizeObserver = new ResizeObserver(entries => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect;
      // Re-render graph with new dimensions
      renderSankey(state, svgRef.current, containerRef.current, animatingEdges);
    }
  });
  
  resizeObserver.observe(containerRef.current);
  return () => resizeObserver.disconnect();
}, [state]);
```

**Benefits**:
- Responds to window resize
- Works with mobile orientation changes
- Adapts to sidebar collapse/expand

---

### 3. **Smart Zoom & Pan** [PRIORITY: MEDIUM]

**Goal**: Allow users to explore large graphs interactively

**Implementation**:
```typescript
// Add D3 zoom behavior
const zoom = d3.zoom()
  .scaleExtent([0.5, 3])  // Min/max zoom levels
  .on('zoom', (event) => {
    mainGroup.attr('transform', event.transform);
  });

svg.call(zoom);

// Add zoom controls UI
<div className="zoom-controls">
  <button onClick={() => svg.transition().call(zoom.scaleBy, 1.2)}>+</button>
  <button onClick={() => svg.transition().call(zoom.scaleBy, 0.8)}>-</button>
  <button onClick={() => svg.transition().call(zoom.transform, d3.zoomIdentity)}>Reset</button>
</div>
```

**Features**:
- Mouse wheel zoom
- Pinch-to-zoom on touch devices
- Pan by dragging
- Reset to fit view
- Zoom buttons for accessibility

---

### 4. **Mobile-Optimized Layout** [PRIORITY: HIGH]

**Goal**: Ensure usability on small screens

**Implementation**:
```typescript
// Mobile-specific adjustments
const mobileAdjustments = {
  nodeWidth: isMobile ? 6 : 8,
  nodePadding: isMobile ? 12 : 18,
  fontSize: isMobile ? 10 : 12,
  leftPadding: isMobile ? 10 : 20,
  rightPadding: isMobile ? 10 : 20,
  minHeight: isMobile ? 600 : 500,  // Taller on mobile for vertical scroll
};

// Enable vertical scrolling on mobile
<div className={`overflow-y-auto ${isMobile ? 'max-h-screen' : ''}`}>
  <svg ... />
</div>
```

**Features**:
- Smaller nodes on mobile
- Reduced padding for more space
- Vertical scrolling when needed
- Touch-friendly interaction zones

---

### 5. **Fit-to-View Automatic Scaling** [PRIORITY: HIGH]

**Goal**: Always show entire graph within viewport

**Implementation**:
```typescript
// Calculate bounding box of all nodes
const nodeBounds = {
  minX: Math.min(...nodes.map(n => n.x0!)),
  maxX: Math.max(...nodes.map(n => n.x1!)),
  minY: Math.min(...nodes.map(n => n.y0!)),
  maxY: Math.max(...nodes.map(n => n.y1!)),
};

const contentWidth = nodeBounds.maxX - nodeBounds.minX;
const contentHeight = nodeBounds.maxY - nodeBounds.minY;

// Scale viewBox to fit content with padding
const padding = 40;
const viewBoxX = nodeBounds.minX - padding;
const viewBoxY = nodeBounds.minY - padding;
const viewBoxWidth = contentWidth + (padding * 2);
const viewBoxHeight = contentHeight + (padding * 2);

svg.attr('viewBox', `${viewBoxX} ${viewBoxY} ${viewBoxWidth} ${viewBoxHeight}`);
```

**Benefits**:
- Entire graph always visible
- No clipped nodes
- Optimal use of space
- Maintains aspect ratio

---

### 6. **Progressive Enhancement** [PRIORITY: MEDIUM]

**Goal**: Gracefully handle edge cases

**Implementation**:
```typescript
// Display warnings/indicators
if (maxNodesInLayer > 20) {
  // Show "Large graph - zoom recommended" message
}

if (containerWidth < 320) {
  // Show "Rotate device for better view" message
}

// Provide alternative views
<button onClick={() => setViewMode('compact')}>Compact View</button>
<button onClick={() => setViewMode('detailed')}>Detailed View</button>
```

**Features**:
- Compact mode for many nodes
- Detailed mode for deep inspection
- User guidance for large graphs
- Responsive messaging

---

### 7. **Performance Optimization** [PRIORITY: MEDIUM]

**Goal**: Maintain smooth rendering with many nodes

**Implementation**:
```typescript
// Debounce resize events
const debouncedResize = useMemo(
  () => debounce(() => renderSankey(...), 150),
  [state]
);

// Virtual scrolling for massive graphs (50+ nodes)
if (nodeCount > 50) {
  // Render only visible portion + buffer
}

// Canvas fallback for very large graphs
if (nodeCount > 100) {
  // Use canvas instead of SVG
}
```

**Benefits**:
- Smooth performance
- Handles large datasets
- Prevents UI lag

---

## Implementation Phases

### Phase 1: Core Visibility (1-2 hours)
- [ ] Dynamic height calculation based on node count
- [ ] Fit-to-view automatic scaling
- [ ] Remove clipPath or make it non-restrictive
- [ ] Mobile padding adjustments

### Phase 2: Interactivity (1-2 hours)
- [ ] Add zoom/pan with D3
- [ ] Zoom control buttons
- [ ] Touch gesture support
- [ ] Reset view functionality

### Phase 3: Responsive Enhancements (1 hour)
- [ ] ResizeObserver integration
- [ ] Orientation change handling
- [ ] Breakpoint-specific optimizations
- [ ] Mobile vertical scrolling

### Phase 4: Polish & Testing (1 hour)
- [ ] Test with 2, 5, 10, 20 nodes
- [ ] Test on mobile, tablet, desktop
- [ ] Test landscape/portrait orientations
- [ ] Performance profiling

---

## Success Criteria

✅ **All nodes visible** on any screen size without manual scrolling  
✅ **Zoom/pan available** for detailed inspection  
✅ **Responsive** to window resize and orientation change  
✅ **Touch-friendly** on mobile devices  
✅ **Performance** maintained with 50+ nodes  
✅ **No clipped content** - all labels readable  
✅ **Accessible** with keyboard navigation  

---

## Files to Modify

1. **frontend/src/components/LiveSankeyGraph.tsx** (primary)
   - Dynamic height calculation
   - Zoom/pan implementation
   - Responsive sizing

2. **frontend/src/components/DCLGraphContainer.tsx** (minor)
   - Container styling adjustments
   - Zoom controls UI

3. **frontend/src/index.css** (optional)
   - Zoom control styles
   - Mobile scrolling classes

---

## Testing Matrix

| Device | Orientation | Nodes | Expected Result |
|--------|-------------|-------|-----------------|
| Mobile (320px) | Portrait | 5 | All visible, scrollable |
| Mobile (375px) | Portrait | 10 | All visible, compact |
| Tablet (768px) | Landscape | 15 | All visible, comfortable |
| Desktop (1920px) | Landscape | 20 | All visible, spacious |
| Desktop (1920px) | Landscape | 50 | Zoom recommended, all accessible |

---

## Risk Assessment

**Low Risk**:
- Dynamic height calculation
- Mobile padding adjustments
- Fit-to-view scaling

**Medium Risk**:
- Zoom/pan interaction (may conflict with existing interactions)
- ResizeObserver (browser compatibility)

**High Risk**:
- Removing clipPath (may cause layout issues)
- Canvas fallback (requires major refactor)

---

## Rollback Strategy

If issues arise:
1. Keep original `minHeight: 500px` as fallback
2. Feature flag for zoom/pan
3. Revert to fixed heights if dynamic calculation fails
4. Preserve existing clipPath logic

---

## Next Steps

**Recommended Approach**: Implement Phase 1 first (core visibility), test thoroughly, then proceed to Phase 2 (interactivity).

**Would you like to proceed with Phase 1 implementation?**
