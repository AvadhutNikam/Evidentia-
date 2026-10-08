import { useEffect, useState } from 'react';
import { CaseStateEngine } from './CaseStateEngine';

/**
 * A custom React hook that forces a component to re-render 
 * whenever the CaseStateEngine notifies listeners of a state change.
 */
export function useCaseState() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const engine = CaseStateEngine.getInstance();
    const unsubscribe = engine.subscribe(() => {
      setTick(t => t + 1);
    });
    return unsubscribe;
  }, []);

  return tick;
}
