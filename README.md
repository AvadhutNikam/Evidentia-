# EVIDENTIA - Investigation Intelligence Platform

This is the frontend foundation for the EVIDENTIA AI-Powered Investigation Intelligence Platform.

## Project Overview
Evidentia is a professional, modern investigation intelligence dashboard designed for investigation agencies, digital forensics teams, and intelligence analysts.

This codebase currently represents the **Frontend Shell**. It provides the UI, navigation, component architecture, and mock data needed to demonstrate the system's capabilities. 

## Technology Stack
- **Framework**: React 18 + Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM
- **Icons**: Lucide React
- **Charts**: Recharts

## Folder Structure
- `/src/components` - Reusable UI elements (`Card`, `Badge`) and layout structures (`Sidebar`, `Topbar`).
- `/src/pages` - The main views for each route.
- `/src/services` - The API abstraction layer. Currently returning mock data with simulated delays.
- `/src/mock-data` - Realistic fake investigation data.
- `/src/types` - Centralized TypeScript interfaces for all entities.

## Running Locally

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

## Current Frontend Status
- Responsive, dark-mode first UI.
- Routing is fully implemented.
- Mock data services are wired up for Cases, Evidence, and Timeline.
- Layout and styling are complete.

## Future FastAPI Integration
The application is designed to easily swap out the mock services in `src/services/` with actual Axios/Fetch calls to a FastAPI backend.
- Replace `await delay()` in `services/index.ts` with API calls.
- Connect to PostgreSQL for persistent data.
- Connect AI services via FastAPI endpoints for Knowledge Graphs and Assistant UI.
