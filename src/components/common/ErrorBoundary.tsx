import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 my-4 rounded-3xl bg-white border border-[#eae4d9] shadow-xs text-center max-w-xl mx-auto space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-[#fdeee9] text-[#d93829] flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6 stroke-[2]" />
          </div>
          <div>
            <h3 className="font-serif font-bold text-lg text-[#191410]">
              {this.props.fallbackTitle || 'Component Encountered an Issue'}
            </h3>
            <p className="text-xs text-[#6e665d] mt-1 leading-relaxed">
              {this.state.error?.message || 'A temporary rendering anomaly occurred. You can reload this view.'}
            </p>
          </div>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Try Again</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
