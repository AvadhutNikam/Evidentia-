import { Outlet } from 'react-router-dom';
import { CaseSidebar } from './CaseSidebar';
import { Topbar } from './Topbar';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { CollaborationProvider } from '../../context/CollaborationContext';
import { StreamingAnalysisProvider } from '../../context/StreamingAnalysisContext';
import { StreamingAnalysisStrip } from '../case/StreamingAnalysisStrip';
import { ActivityFeedDrawer } from '../collaboration/ActivityFeedDrawer';
import { ConflictModal } from '../collaboration/ConflictModal';
import { FloatingAiAssistant } from '../case/FloatingAiAssistant';

export function CaseLayout() {
  return (
    <CollaborationProvider>
      <StreamingAnalysisProvider>
        <div className="h-screen w-full flex bg-[#faf7f2] overflow-hidden text-[#191410]">
          <CaseSidebar />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
            <Topbar />
            <main className="flex-1 overflow-y-auto p-6 scroll-smooth bg-[#faf7f2]">
              <div className="max-w-7xl mx-auto h-full">
                <ErrorBoundary fallbackTitle="Case View Error">
                  <StreamingAnalysisStrip />
                  <Outlet />
                </ErrorBoundary>
              </div>
            </main>
            <ActivityFeedDrawer />
            <ConflictModal />
            <FloatingAiAssistant />
          </div>
        </div>
      </StreamingAnalysisProvider>
    </CollaborationProvider>
  );
}
