import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { GlobalLayout } from './components/layout/GlobalLayout';
import { CaseLayout } from './components/layout/CaseLayout';
import { GlobalErrorBanner } from './components/common/GlobalErrorBanner';
import { CommandPalette } from './components/common/CommandPalette';
import { ALL_NAV_ITEMS } from './config/caseNav';

// Fallback loader for station conditions
function PageLoadingFallback() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-[50vh] p-8 text-center animate-fade-in select-none">
      <div className="w-9 h-9 border-3 border-[#d93829]/20 border-t-[#d93829] rounded-full animate-spin mb-3" />
      <span className="font-serif font-bold text-base text-[#191410] tracking-tight">Evidentia AI</span>
      <span className="text-xs text-[#70685e] mt-1 font-mono">Loading module...</span>
    </div>
  );
}

// Global Pages (Lazy-Loaded)
const Dashboard = lazy(() => import('./pages/global/Dashboard').then(m => ({ default: m.Dashboard })));
const Cases = lazy(() => import('./pages/global/Cases').then(m => ({ default: m.Cases })));
const Osint = lazy(() => import('./pages/global/Osint').then(m => ({ default: m.Osint })));
const Search = lazy(() => import('./pages/global/Search').then(m => ({ default: m.Search })));
const Reports = lazy(() => import('./pages/global/Reports').then(m => ({ default: m.Reports })));
const Settings = lazy(() => import('./pages/global/Settings').then(m => ({ default: m.Settings })));
const Evaluation = lazy(() => import('./pages/global/Evaluation').then(m => ({ default: m.Evaluation })));
const ModelCard = lazy(() => import('./pages/global/ModelCard').then(m => ({ default: m.ModelCard })));
const Login = lazy(() => import('./pages/global/Login').then(m => ({ default: m.Login })));
const SystemHealth = lazy(() => import('./pages/global/SystemHealth').then(m => ({ default: m.SystemHealth })));
const MalkhanaRegister = lazy(() => import('./pages/global/MalkhanaRegister').then(m => ({ default: m.MalkhanaRegister })));

// Case Pages (Lazy-Loaded)
const CaseOverview = lazy(() => import('./pages/case/CaseOverview').then(m => ({ default: m.CaseOverview })));
const TodaysPriorities = lazy(() => import('./pages/case/TodaysPriorities').then(m => ({ default: m.TodaysPriorities })));
const CaseFile = lazy(() => import('./pages/case/CaseFile').then(m => ({ default: m.CaseFile })));
const LinkAnalysis = lazy(() => import('./pages/case/LinkAnalysis').then(m => ({ default: m.LinkAnalysis })));
const DefenseStressTest = lazy(() => import('./pages/case/DefenseStressTest').then(m => ({ default: m.DefenseStressTest })));
const EvidenceList = lazy(() => import('./pages/case/EvidenceList').then(m => ({ default: m.EvidenceList })));
const EvidenceDetails = lazy(() => import('./pages/case/EvidenceDetails').then(m => ({ default: m.EvidenceDetails })));
const CaseDataQuality = lazy(() => import('./pages/case/CaseDataQuality').then(m => ({ default: m.CaseDataQuality })));
const AnalysisWorkspace = lazy(() => import('./pages/case/AnalysisWorkspace').then(m => ({ default: m.AnalysisWorkspace })));
const Timeline = lazy(() => import('./pages/case/Timeline').then(m => ({ default: m.Timeline })));
const Entities = lazy(() => import('./pages/case/Entities').then(m => ({ default: m.Entities })));
const KnowledgeGraph = lazy(() => import('./pages/case/KnowledgeGraph').then(m => ({ default: m.KnowledgeGraph })));
const Contradictions = lazy(() => import('./pages/case/Contradictions').then(m => ({ default: m.Contradictions })));
const Hypotheses = lazy(() => import('./pages/case/Hypotheses').then(m => ({ default: m.Hypotheses })));
const SuspectsAndTheories = lazy(() => import('./pages/case/SuspectsAndTheories').then(m => ({ default: m.SuspectsAndTheories })));
const MapAndTimeline = lazy(() => import('./pages/case/MapAndTimeline').then(m => ({ default: m.MapAndTimeline })));
const InvestigationPlan = lazy(() => import('./pages/case/InvestigationPlan').then(m => ({ default: m.InvestigationPlan })));
const Interviews = lazy(() => import('./pages/case/Interviews').then(m => ({ default: m.Interviews })));
const CaseMap = lazy(() => import('./pages/case/CaseMap').then(m => ({ default: m.CaseMap })));
const AiAssistant = lazy(() => import('./pages/case/AiAssistant').then(m => ({ default: m.AiAssistant })));
const CaseReports = lazy(() => import('./pages/case/CaseReports').then(m => ({ default: m.CaseReports })));
const ActivityLog = lazy(() => import('./pages/case/ActivityLog').then(m => ({ default: m.ActivityLog })));
const SuspectProfile = lazy(() => import('./pages/case/SuspectProfile').then(m => ({ default: m.SuspectProfile })));
const ScoringConfiguration = lazy(() => import('./pages/case/ScoringConfiguration').then(m => ({ default: m.ScoringConfiguration })));
const ResponsibleUse = lazy(() => import('./pages/case/ResponsibleUse').then(m => ({ default: m.ResponsibleUse })));
const Handover = lazy(() => import('./pages/case/Handover').then(m => ({ default: m.Handover })));
const ChargesheetAssistant = lazy(() => import('./pages/case/ChargesheetAssistant').then(m => ({ default: m.ChargesheetAssistant })));
const CrossCaseIntelligence = lazy(() => import('./pages/case/CrossCaseIntelligence').then(m => ({ default: m.CrossCaseIntelligence })));
const CDRFinancialAnalytics = lazy(() => import('./pages/case/CDRFinancialAnalytics').then(m => ({ default: m.CDRFinancialAnalytics })));
const MobileFieldCapture = lazy(() => import('./pages/case/MobileFieldCapture').then(m => ({ default: m.MobileFieldCapture })));
const LiveConnectors = lazy(() => import('./pages/case/LiveConnectors').then(m => ({ default: m.LiveConnectors })));
const SituationBoard = lazy(() => import('./pages/case/SituationBoard').then(m => ({ default: m.SituationBoard })));
const IntakeReviewInbox = lazy(() => import('./pages/case/IntakeReviewInbox').then(m => ({ default: m.IntakeReviewInbox })));

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <GlobalErrorBanner />
        <CommandPalette />
        <Suspense fallback={<PageLoadingFallback />}>
          <Routes>
          <Route path="/login" element={<Login />} />

          {/* Global Workspace Routes */}
          <Route path="/" element={<GlobalLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="cases" element={<Cases />} />
          <Route path="osint" element={<Osint />} />
          <Route path="search" element={<Search />} />
          <Route path="reports" element={<Reports />} />
          <Route path="evaluation" element={<Evaluation />} />
          <Route path="model-card" element={<ModelCard />} />
          <Route path="system-health" element={<SystemHealth />} />
          <Route path="malkhana" element={<MalkhanaRegister />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Fullscreen Standalone Case Wall / Situation Board for Team Rooms & Second Monitors */}
        <Route path="/cases/:caseId/wall" element={<SituationBoard />} />
        <Route path="/cases/:caseId/situation-board" element={<SituationBoard />} />

        {/* Case Workspace Routes */}
        <Route path="/cases/:caseId" element={<CaseLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<CaseOverview />} />
          <Route path="priorities" element={<TodaysPriorities />} />
          <Route path="case-file" element={<CaseFile />} />
          <Route path="link-analysis" element={<LinkAnalysis />} />
          <Route path="defense-stress-test" element={<DefenseStressTest />} />

          {/* Automatic Backward-Compatible Redirects */}
          <Route path="details" element={<Navigate to="case-file" replace />} />
          <Route path="fir" element={<Navigate to="case-file" replace />} />
          <Route path="graph" element={<Navigate to="link-analysis?tab=network" replace />} />
          <Route path="entities" element={<Navigate to="link-analysis?tab=entities" replace />} />
          <Route path="analysis" element={<Navigate to="link-analysis?tab=workspace" replace />} />
          <Route path="workspace" element={<Navigate to="link-analysis?tab=workspace" replace />} />
          <Route path="cross-case" element={<Navigate to="link-analysis?tab=cross-case" replace />} />
          <Route path="cross-case-intelligence" element={<Navigate to="link-analysis?tab=cross-case" replace />} />
          <Route path="suspects" element={<Navigate to="hypotheses?tab=profiles" replace />} />
          <Route path="theories" element={<Navigate to="hypotheses?tab=theories" replace />} />
          <Route path="contradictions" element={<Navigate to="hypotheses?tab=contradictions" replace />} />
          <Route path="statement-conflicts" element={<Navigate to="hypotheses?tab=contradictions" replace />} />
          <Route path="map" element={<Navigate to="timeline?tab=map" replace />} />
          <Route path="case-map" element={<Navigate to="timeline?tab=map" replace />} />
          <Route path="timeline-map" element={<Navigate to="timeline?tab=timeline" replace />} />
          <Route path="devils-advocate" element={<Navigate to="defense-stress-test" replace />} />
          <Route path="stress-test" element={<Navigate to="defense-stress-test" replace />} />
          <Route path="plan" element={<Navigate to="investigation-plan" replace />} />
          <Route path="missing-evidence" element={<Navigate to="investigation-plan" replace />} />
          <Route path="gaps" element={<Navigate to="investigation-plan" replace />} />
          <Route path="config" element={<Navigate to="/settings?section=scoring_config" replace />} />
          <Route path="scoring-config" element={<Navigate to="/settings?section=scoring_config" replace />} />
          <Route path="responsible-use" element={<Navigate to="/settings?section=responsible_use" replace />} />

          {/* Dynamic Automatic Backward-Compatible Redirects from Config */}
          {ALL_NAV_ITEMS.flatMap(item => 
            (item.replaces || []).map(oldP => (
              <Route 
                key={`redirect-${oldP}`} 
                path={oldP} 
                element={<Navigate to={item.path} replace />} 
              />
            ))
          )}

          {/* Core Case Pages */}
          <Route path="wall" element={<SituationBoard />} />
          <Route path="intake" element={<IntakeReviewInbox />} />
          <Route path="evidence" element={<EvidenceList />} />
          <Route path="evidence/:evidenceId" element={<EvidenceDetails />} />
          <Route path="malkhana" element={<MalkhanaRegister />} />
          <Route path="data-quality" element={<CaseDataQuality />} />
          <Route path="evidence/quality" element={<CaseDataQuality />} />
          <Route path="field-capture" element={<MobileFieldCapture />} />
          <Route path="connectors" element={<LiveConnectors />} />
          <Route path="timeline" element={<MapAndTimeline />} />
          <Route path="map-and-timeline" element={<MapAndTimeline />} />
          <Route path="hypotheses" element={<SuspectsAndTheories />} />
          <Route path="suspects-and-theories" element={<SuspectsAndTheories />} />
          <Route path="investigation-plan" element={<InvestigationPlan />} />
          <Route path="interviews" element={<Interviews />} />
          <Route path="assistant" element={<AiAssistant />} />
          <Route path="handover" element={<Handover />} />
          <Route path="chargesheet" element={<ChargesheetAssistant />} />
          <Route path="telecom-financial" element={<CDRFinancialAnalytics />} />
          <Route path="reports" element={<CaseReports />} />
          <Route path="activity" element={<ActivityLog />} />
        </Route>
      </Routes>
      </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
