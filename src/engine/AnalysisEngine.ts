import { hypothesisService } from '../services';

export class AnalysisEngine {
  /**
   * Real Competing Hypothesis Engine (ACH Methodology) via FastAPI & Gemini:
   * Collects Case + Evidence Exhibits + Entities + Timeline Events.
   * Gemini generates divergent plausible competing hypotheses and evaluates
   * EVERY evidence exhibit against each hypothesis, storing results in PostgreSQL.
   */
  public static async runACHAnalysis(caseId: string): Promise<void> {
    try {
      console.log(`[ACH Engine] Initiating Real Backend Analysis of Competing Hypotheses for case: ${caseId}`);
      await hypothesisService.analyzeHypotheses(caseId);
      console.log(`[ACH Engine] Real backend ACH analysis completed successfully for ${caseId}`);
    } catch (error) {
      console.error('ACH Analysis failed:', error);
    }
  }
}
