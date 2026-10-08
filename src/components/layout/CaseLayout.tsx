import { Outlet } from 'react-router-dom';
import { CaseSidebar } from './CaseSidebar';
import { Topbar } from './Topbar';
import { ErrorBoundary } from '../common/ErrorBoundary';

export function CaseLayout() {
  return (
    <div className="h-screen w-full flex bg-[#faf7f2] overflow-hidden text-[#191410]">
      <CaseSidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6 scroll-smooth bg-[#faf7f2]">
          <div className="max-w-7xl mx-auto h-full">
            <ErrorBoundary fallbackTitle="Case View Error">
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}
