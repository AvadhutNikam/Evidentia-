# Evidentia Frontend Foundation Implementation Plan

This document outlines the plan to build the frontend foundation for the Evidentia AI-Powered Investigation Intelligence Platform.

## Goal
Build a professional, modern, dark-first investigation intelligence dashboard using React, Vite, TypeScript, and Tailwind CSS. The frontend will be fully modular with a clean API abstraction layer ready for future FastAPI integration.

## Proposed Architecture & Tech Stack
- **Framework**: React 18 + Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS (Dark theme prioritized)
- **Routing**: React Router DOM
- **Icons**: Lucide React
- **Charts**: Recharts
- **State/Data**: React Context / Hooks (Local state with mock data for now)

## Directory Structure
```text
src/
├── components/
│   ├── layout/        # Sidebar, Topbar, MainLayout
│   ├── ui/            # Reusable components (Card, Button, Badge, Modal, etc.)
│   └── specific/      # Domain-specific components (TimelineEvent, EntityCard)
├── pages/             # Route components (Dashboard, Cases, Evidence, etc.)
├── services/          # API abstraction layer (caseService, evidenceService)
├── types/             # Centralized TypeScript interfaces
├── mock-data/         # Realistic investigation mock data
├── utils/             # Helper functions (formatting, clsx + tailwind-merge)
├── App.tsx            # Main application component & routing
└── main.tsx           # Entry point
```

## Implementation Steps

### Phase 1: Initialization & Setup
1. Scaffold a new Vite project with React + TS in the current directory (`C:/Users/prati/OneDrive/Documents/evidentia`).
2. Install dependencies: `react-router-dom`, `lucide-react`, `recharts`, `clsx`, `tailwind-merge`.
3. Install and configure Tailwind CSS (with specific deep dark colors and enterprise-grade aesthetics).

### Phase 2: Core Types & Mock Data
1. Define comprehensive TypeScript interfaces in `src/types/index.ts` (Case, Evidence, Person, Location, etc.).
2. Create realistic mock data sets in `src/mock-data/` to populate the application without a backend.
3. Implement the `src/services/` API abstraction layer. These services will return Promises that resolve with mock data, simulating actual API calls.

### Phase 3: Layout & Reusable UI Components
1. Build base UI components: `Card`, `Badge`, `Button`, `DataTable`, `LoadingState`, etc.
2. Build layout components: `Sidebar` (collapsible, navigation links), `Topbar` (search, profile, breadcrumbs), and `MainLayout`.

### Phase 4: Page Implementation
Implement the required pages using the mock data services and UI components:
1. **Dashboard**: High-level metrics, Recharts integration, recent cases, and activity timeline.
2. **Cases Management**: List view, filtering, and a detailed Case view with tabs.
3. **Evidence Management**: Upload zone, status indicators, evidence list, and detailed evidence view.
4. **Timeline**: Chronological event visualization.
5. **Knowledge Graph**: A simulated interactive graph view (using basic layout or a lightweight graph component).
6. **OSINT Intelligence**: Tools dashboard with search inputs and placeholders.
7. **Interview Analysis**: Mock audio processing view with timestamped transcript.
8. **Case Map**: Geographic mapping placeholder layout.
9. **AI Assistant**: A chat interface tailored for case investigations.
10. **Reports & Settings**: Basic generation placeholders and preference forms.

### Phase 5: Routing & Polish
1. Set up all routes in `App.tsx` following the defined path structure.
2. Ensure responsive design (desktop-first, but working on smaller screens).
3. Final review of the aesthetic (professional, technical, minimal, no generic SaaS looks).

### Phase 6: Documentation
1. Create a detailed `README.md` covering the project, tech stack, running instructions, and the future integration path with FastAPI.

## Open Questions
- For the Knowledge Graph visualization, since we need to create a frontend visualization, I will use a simple custom SVG or CSS-based mock graph for now to avoid introducing heavy unrequested dependencies like `react-flow-renderer` unless you prefer I add a library for it. Is a custom visual mockup acceptable for this stage?
- Should we use standard system fonts (Inter/Roboto via Google Fonts) to enhance the professional look?

## User Review Required
> [!IMPORTANT]
> Please review the proposed architecture and steps above. Once approved, I will begin initializing the project and executing the plan.
