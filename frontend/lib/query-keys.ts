export const queryKeys = {
  projects: () => ["projects"] as const,
  project: (projectId: number) => ["projects", projectId] as const,
  evidence: (projectId: number) => ["projects", projectId, "evidence"] as const,
  evidenceItem: (projectId: number, evidenceId: number) =>
    ["projects", projectId, "evidence", evidenceId] as const,
  personas: (projectId: number) => ["projects", projectId, "personas"] as const,
  persona: (projectId: number, personaId: number) =>
    ["projects", projectId, "personas", personaId] as const,
  experiments: (projectId: number) => ["projects", projectId, "experiments"] as const,
  experiment: (projectId: number, experimentId: number) =>
    ["projects", projectId, "experiments", experimentId] as const,
  runs: (projectId: number, experimentId: number) =>
    ["projects", projectId, "experiments", experimentId, "runs"] as const,
  run: (projectId: number, experimentId: number, runId: number) =>
    ["projects", projectId, "experiments", experimentId, "runs", runId] as const,
  analysis: (projectId: number, experimentId: number) =>
    ["projects", projectId, "experiments", experimentId, "analysis"] as const,
  insights: (projectId: number, experimentId: number) =>
    ["projects", projectId, "experiments", experimentId, "insights"] as const,
  decisionMemo: (projectId: number, experimentId: number) =>
    ["projects", projectId, "experiments", experimentId, "decision-memo"] as const,
  humanFeedback: (projectId: number, experimentId: number) =>
    ["projects", projectId, "experiments", experimentId, "human-feedback"] as const,
  humanFeedbackItem: (projectId: number, experimentId: number, feedbackId: number) =>
    ["projects", projectId, "experiments", experimentId, "human-feedback", feedbackId] as const,
  humanComparison: (projectId: number, experimentId: number) =>
    ["projects", projectId, "experiments", experimentId, "human-feedback", "comparison"] as const,
};
