import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { GlobalLayout } from './components/layout/GlobalLayout';
import { CaseLayout } from './components/layout/CaseLayout';

// Global Pages
import { Dashboard } from './pages/global/Dashboard';
import { Cases } from './pages/global/Cases';
import { Osint } from './pages/global/Osint';
import { Search } from './pages/global/Search';
import { Reports } from './pages/global/Reports';
import { Settings } from './pages/global/Settings';
import { Evaluation } from './pages/global/Evaluation';
import { Login } from './pages/global/Login';

// Case Pages
import { CaseOverview } from './pages/case/CaseOverview';
import { EvidenceList } from './pages/case/EvidenceList';
import { EvidenceDetails } from './pages/case/EvidenceDetails';
import { AnalysisWorkspace } from './pages/case/AnalysisWorkspace';
import { Timeline } from './pages/case/Timeline';
import { Entities } from './pages/case/Entities';
import { KnowledgeGraph } from './pages/case/KnowledgeGraph';
import { Contradictions } from './pages/case/Contradictions';
import { Hypotheses } from './pages/case/Hypotheses';
import { InvestigationPlan } from './pages/case/InvestigationPlan';
import { Interviews } from './pages/case/Interviews';
import { CaseMap } from './pages/case/CaseMap';
import { AiAssistant } from './pages/case/AiAssistant';
import { CaseReports } from './pages/case/CaseReports';
import { ActivityLog } from './pages/case/ActivityLog';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
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
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Case Workspace Routes */}
        <Route path="/cases/:caseId" element={<CaseLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<CaseOverview />} />
          <Route path="evidence" element={<EvidenceList />} />
          <Route path="evidence/:evidenceId" element={<EvidenceDetails />} />
          <Route path="analysis" element={<AnalysisWorkspace />} />
          <Route path="timeline" element={<Timeline />} />
          <Route path="entities" element={<Entities />} />
          <Route path="graph" element={<KnowledgeGraph />} />
          <Route path="contradictions" element={<Contradictions />} />
          <Route path="hypotheses" element={<Hypotheses />} />
          <Route path="investigation-plan" element={<InvestigationPlan />} />
          <Route path="interviews" element={<Interviews />} />
          <Route path="map" element={<CaseMap />} />
          <Route path="assistant" element={<AiAssistant />} />
          <Route path="reports" element={<CaseReports />} />
          <Route path="activity" element={<ActivityLog />} />
        </Route>
      </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
