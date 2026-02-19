# TPRD-2026-02-18-dependency-graph

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-dependency-graph
Version:        1.0
Status:         Draft
Feature Name:   Dependency Graph Visualization
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Provide an interactive visual representation of the entire service dependency landscape, enabling teams to understand upstream/downstream dependencies, identify single points of failure, and assess blast radius during incidents.
- **Technical Scope**: Client-side D3.js force-directed graph visualization powered by the GraphQL `dependencyGraph` query. Full graph view (all entities) and product-scoped mini-graphs. Interactive features: zoom, pan, drag, hover tooltips, click-to-navigate, entity type filtering, and operational status coloring.
- **Success Criteria**: Graph renders 200+ nodes smoothly (60fps). Users can identify dependencies at a glance via color coding and layout. Product-scoped graphs isolate relevant subsets.
- **Complexity Estimate**: M — D3.js force simulation with custom node types, interactive controls, and GraphQL data integration.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Full dependency graph (all products, services, components, resources)
- Product-scoped mini-graph (entities related to a single product)
- D3.js force-directed layout with collision detection
- Node types: Products (hexagon), Services (circle), Components (square), Resources (diamond)
- Node coloring by operational status (green/yellow/orange/red)
- Edge types: depends_on (solid arrow), contains (dashed), uses (dotted)
- Interactive controls: zoom, pan, drag nodes, reset view
- Hover tooltip: entity name, type, operational status, team
- Click node: navigate to entity detail view
- Filter panel: toggle visibility by entity type, by operational status
- Sidebar legend showing node/edge types and colors
- Search within graph: highlight matching nodes
- Fullscreen mode

### 3.2 Out of Scope
- 3D graph visualization
- Historical graph snapshots (dependency changes over time)
- Automated layout algorithms beyond force-directed (hierarchical, radial)
- Graph editing (adding/removing edges from graph UI)
- Real-time graph updates via WebSocket

### 3.3 Assumptions
- D3.js 7 runs client-side within the Vue component
- Graph data fetched via GraphQL `dependencyGraph` query
- Maximum practical graph size: ~500 nodes (beyond this, product filter should be used)
- Layout is non-deterministic (force simulation); positions are not persisted

### 3.4 Dependencies
- TPRD-2026-02-18-graphql-api (`dependencyGraph` query, `impactAnalysis` query)
- TPRD-2026-02-18-frontend-application (Vue component framework)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`:
- D3.js 7.x for force simulation and SVG rendering
- Vue 3 Composition API for component wrapper
- GraphQL for data fetching

### 4.2 Architecture

```
DependencyGraphView.vue
├── GraphControls.vue        # Filter panel, zoom buttons, search
├── GraphLegend.vue          # Node/edge type legend
├── DependencyGraph.vue      # D3.js SVG canvas
│   ├── D3 force simulation
│   ├── SVG nodes (shapes by type)
│   ├── SVG edges (arrows by relationship)
│   └── Tooltips
└── GraphSidebar.vue         # Selected node detail panel
```

### 4.3 GraphQL Data Shape

The `dependencyGraph` query returns:
```typescript
interface DependencyGraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

interface GraphNode {
  id: string
  name: string
  entityType: 'product' | 'service' | 'component' | 'resource'
  operationalStatus: 'operational' | 'degraded' | 'partial_outage' | 'major_outage'
  typeDetail: string | null  // e.g., "api", "library", "kubernetes"
}

interface GraphEdge {
  sourceId: string
  targetId: string
  relationship: 'depends_on' | 'contains' | 'uses' | 'assigned_to'
}
```

### 4.4 D3.js Implementation Specification

#### Force Simulation Configuration

```typescript
const simulation = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(edges)
    .id((d: any) => d.id)
    .distance(100)
    .strength(0.5)
  )
  .force('charge', d3.forceManyBody()
    .strength(-300)
    .distanceMax(500)
  )
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(40))
  .force('x', d3.forceX(width / 2).strength(0.05))
  .force('y', d3.forceY(height / 2).strength(0.05))
```

#### Node Shapes by Entity Type

| Entity Type | Shape | Size | SVG Element |
|------------|-------|------|-------------|
| Product | Hexagon | 30px radius | `<polygon>` |
| Service | Circle | 20px radius | `<circle>` |
| Component | Rounded Square | 16px side | `<rect rx="4">` |
| Resource | Diamond | 18px | `<polygon>` rotated 45° |

#### Node Colors by Operational Status

| Status | Fill Color | Stroke Color |
|--------|-----------|-------------|
| operational | `#10b981` (green-500) | `#059669` (green-600) |
| degraded | `#f59e0b` (amber-500) | `#d97706` (amber-600) |
| partial_outage | `#f97316` (orange-500) | `#ea580c` (orange-600) |
| major_outage | `#ef4444` (red-500) | `#dc2626` (red-600) |

#### Edge Styles by Relationship Type

| Relationship | Line Style | Arrow | Color |
|-------------|-----------|-------|-------|
| depends_on | Solid | ▶ (filled) | `#6b7280` (gray-500) |
| contains | Dashed (4,4) | ▷ (open) | `#9ca3af` (gray-400) |
| uses | Dotted (2,4) | ▷ (open) | `#9ca3af` (gray-400) |

#### Interaction Behaviors

| Interaction | Behavior |
|------------|----------|
| Hover node | Show tooltip with name, type, status, team. Highlight connected edges. Dim non-connected nodes. |
| Click node | Select node. Show detail in sidebar. Highlight all upstream/downstream dependencies (2 levels). |
| Double-click node | Navigate to entity detail page |
| Drag node | Move node, simulation re-heats |
| Scroll wheel | Zoom in/out (bounded: 0.25x – 4x) |
| Click + drag background | Pan the canvas |
| Escape | Deselect node, reset highlights |

### 4.5 Component Specifications

#### DependencyGraph.vue (Core D3 Component)

```vue
<template>
  <div ref="containerRef" class="w-full h-full relative">
    <svg ref="svgRef" class="w-full h-full">
      <defs>
        <!-- Arrow markers for edge types -->
        <marker id="arrow-depends" viewBox="0 0 10 10" refX="25" refY="5"
                markerWidth="8" markerHeight="8" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#6b7280" />
        </marker>
        <marker id="arrow-contains" viewBox="0 0 10 10" refX="25" refY="5"
                markerWidth="8" markerHeight="8" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="#9ca3af" />
        </marker>
      </defs>
      <g ref="graphGroupRef">
        <!-- Edges rendered here -->
        <!-- Nodes rendered here -->
      </g>
    </svg>
    <!-- Tooltip overlay -->
    <div v-if="hoveredNode" class="absolute pointer-events-none bg-gray-900 text-white text-sm rounded-lg px-3 py-2 shadow-lg"
         :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }">
      <div class="font-semibold">{{ hoveredNode.name }}</div>
      <div class="text-gray-300">{{ hoveredNode.entityType }} · {{ hoveredNode.typeDetail }}</div>
      <div class="flex items-center gap-1 mt-1">
        <span class="w-2 h-2 rounded-full" :class="statusColor(hoveredNode.operationalStatus)"></span>
        {{ hoveredNode.operationalStatus }}
      </div>
    </div>
  </div>
</template>
```

**Lifecycle:**
1. `onMounted`: Initialize SVG, fetch graph data, create simulation
2. `watch(graphData)`: Rebuild simulation when data changes (e.g., product filter)
3. `onUnmounted`: Stop simulation, clean up event listeners

**Performance Optimization:**
- Use `requestAnimationFrame` for tick updates
- Throttle hover events to 16ms
- For graphs > 300 nodes: reduce `alpha` decay for faster stabilization and disable collision force
- Use `transform` on the group element for zoom/pan (not individual elements)

#### GraphControls.vue

```
┌──────────────────────────────────┐
│ 🔍 Search: [_______________]    │
│                                  │
│ Entity Types:                    │
│ ☑ Products   ☑ Services         │
│ ☑ Components ☑ Resources        │
│                                  │
│ Status:                          │
│ ☑ Operational  ☑ Degraded       │
│ ☑ Partial      ☑ Outage        │
│                                  │
│ Product Scope:                   │
│ [All Products        ▼]         │
│                                  │
│ [🔄 Reset] [⬜ Fullscreen]      │
│ [➕ Zoom In] [➖ Zoom Out]       │
└──────────────────────────────────┘
```

#### GraphLegend.vue

```
┌──────────────────────┐
│ Nodes:               │
│ ⬡ Product            │
│ ● Service            │
│ ■ Component          │
│ ◆ Resource           │
│                      │
│ Status:              │
│ 🟢 Operational       │
│ 🟡 Degraded          │
│ 🟠 Partial Outage    │
│ 🔴 Major Outage      │
│                      │
│ Edges:               │
│ ── depends_on        │
│ -- contains          │
│ ·· uses              │
└──────────────────────┘
```

#### GraphSidebar.vue (Selected Node Detail)

When a node is clicked, show in a right sidebar:
- Entity name and type
- Operational status with badge
- Team name (linked)
- Direct dependencies (upstream): list with status badges
- Direct dependents (downstream): list with status badges
- Active incidents affecting this entity
- "View Details" button → navigate to entity detail page
- "Impact Analysis" button → highlight full dependency chain

### 4.6 Product-Scoped Mini-Graph

In the Product Detail View, a smaller version of the dependency graph shows only:
- The product node (center)
- All services belonging to the product
- Components used by those services
- Resources used by those services
- Dependencies between above entities

This uses the same `DependencyGraph.vue` component with:
- `productId` prop triggering the scoped GraphQL query
- Reduced canvas size (e.g., 600×400px)
- Simplified controls (no filter panel, just zoom)

## 5. SECURITY REQUIREMENTS

- Graph data fetched via authenticated GraphQL endpoint (JWT required)
- No sensitive data in tooltips (no internal IPs, credentials, etc.)
- Entity attributes are NOT shown in the graph — only name, type, status

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests (Vitest)
- Graph data transformation: raw GraphQL response → D3 node/edge format
- Filter logic: verify nodes hidden/shown based on entity type and status filters
- Search logic: verify node matching by name
- Status color mapping: verify correct color for each status

### 6.2 Component Tests (Vue Test Utils)
- GraphControls: verify filter checkbox interactions
- GraphLegend: verify all items rendered
- GraphSidebar: verify selected node data displayed

### 6.3 E2E Tests (Playwright)
- Navigate to graph page, verify SVG rendered with nodes
- Apply product filter, verify graph updates
- Search for entity name, verify highlighting
- Click node, verify sidebar shows details
- Double-click node, verify navigation to detail page

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Graph with 200 nodes renders at 60fps during simulation. Initial render < 2 seconds including data fetch.
- **Accessibility**: Nodes are keyboard-navigable (Tab to cycle, Enter to select, Escape to deselect). Status conveyed by shape AND color (not color alone).
- **Responsiveness**: Graph fills available container. Controls collapse on smaller screens.

## 8. MIGRATION & DEPLOYMENT

- No backend changes needed (uses existing GraphQL API)
- Graph is part of the frontend SPA bundle
- D3.js is tree-shaken — only import used modules (`d3-force`, `d3-selection`, `d3-zoom`, `d3-drag`, `d3-shape`)

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create TypeScript types for graph data (`types/graph.ts`)
2. Create GraphQL client for `dependencyGraph` query
3. Create Pinia graph store
4. Create DependencyGraph.vue core D3 component
5. Create GraphControls.vue
6. Create GraphLegend.vue
7. Create GraphSidebar.vue
8. Create DependencyGraphView.vue (assembles all)
9. Integrate mini-graph into ProductDetailView
10. Write tests

### File Creation Plan

```
frontend/src/types/graph.ts
frontend/src/api/graphql.ts                    # GraphQL client
frontend/src/stores/graph.ts
frontend/src/views/DependencyGraphView.vue
frontend/src/components/graph/
  DependencyGraph.vue                          # Core D3 component
  GraphControls.vue
  GraphLegend.vue
  GraphSidebar.vue
  useGraphSimulation.ts                        # D3 simulation composable
  useGraphInteractions.ts                      # Zoom, pan, drag composable
  graphUtils.ts                                # Shape generators, color maps
```

### Do NOT
- Do NOT import the entire D3 library — only import needed modules
- Do NOT render graph using DOM manipulation outside the SVG — use D3's data join pattern
- Do NOT store node positions in Pinia — they live in the D3 simulation only
- Do NOT block the main thread — use `requestAnimationFrame` for simulation ticks
- Do NOT render text labels on nodes when zoomed out (performance) — show only on hover or when zoomed in

### Verify
- [ ] Graph renders correctly with sample data (products, services, components, resources)
- [ ] Node shapes match entity types
- [ ] Node colors match operational status
- [ ] Edge styles match relationship types
- [ ] Hover shows tooltip with correct data
- [ ] Click selects node and shows sidebar
- [ ] Double-click navigates to entity detail
- [ ] Product filter scopes graph correctly
- [ ] Entity type checkboxes hide/show nodes
- [ ] Search highlights matching nodes
- [ ] Zoom and pan work smoothly
- [ ] Graph with 200 nodes maintains 60fps
- [ ] Fullscreen mode works

## 10. OPEN QUESTIONS

None.
