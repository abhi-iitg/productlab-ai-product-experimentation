/**
 * Fictional, professional, portfolio-safe test content for a simple
 * software product concept. No real people, companies, or proprietary
 * research — see the Stage 9A brief's "Test Data" requirements.
 */

export const PROJECT = {
  name: "Field Notes Sync",
  problemStatement:
    "Field technicians re-enter the same job notes twice: once on a paper checklist at the " +
    "job site, and again into the reporting app once they are back in cell range, because the " +
    "app has no offline mode.",
  targetUser: "Independent HVAC and appliance repair technicians who visit six to ten sites a day.",
  productHypothesis:
    "An offline-first checklist that syncs automatically once a technician is back in range " +
    "will cut end-of-day paperwork time roughly in half.",
  successMetric: "Average minutes spent on end-of-day paperwork per technician per day.",
  updatedProblemStatement:
    "Field technicians re-enter the same job notes twice, and the delay between the site visit " +
    "and the office sync means dispatchers often see stale job status for hours.",
};

export const EVIDENCE_PRIMARY = {
  title: "Interview with a mobile HVAC technician",
  content:
    "The technician described re-entering the same job notes twice: once on a paper checklist " +
    "at the site, and again into the reporting app back at the truck, because the app has no " +
    "offline mode. They estimated this costs 20 to 30 minutes per day and said they would pay " +
    "for a tool that synced automatically once they were back in range.",
  sourceLabel: "Interview #4",
};

export const EVIDENCE_PRIMARY_EDITED = {
  title: "Interview with a mobile HVAC technician (follow-up)",
  content:
    "Follow-up note: the technician also mentioned that dispatchers sometimes call mid-route " +
    "asking for a status update, because the office system does not reflect site visits until " +
    "the evening sync.",
};

export const EVIDENCE_SECONDARY = {
  title: "Support ticket about missed sync",
  content:
    "A technician reported losing a full day of job notes when their phone ran out of storage " +
    "before the evening sync completed, and asked for a way to sync partial progress during " +
    "the day instead of only at the end.",
};

export const EXPERIMENT = {
  name: "Offline checklist concept comparison",
  objective: "Compare a fully offline checklist against a lightweight background-sync checklist.",
  hypothesis: "A fully offline-first checklist will feel more trustworthy than partial background sync.",
  scenario:
    "You are a technician finishing a job site visit with no cell signal. Walk through how you " +
    "would record your notes and what you'd expect to happen once you're back in range.",
  evaluationCriteria: ["Clarity of the offline behavior", "Perceived reliability"],
  variantAName: "Fully offline checklist",
  variantADescription:
    "The checklist works entirely offline and queues every change locally, syncing everything " +
    "automatically the next time the app detects a connection.",
  variantBName: "Background partial sync",
  variantBDescription:
    "The checklist syncs each completed section in the background whenever a brief connection " +
    "window is available, rather than waiting for the full visit to finish.",
};

export const HUMAN_FEEDBACK = {
  participantLabel: "Participant 1",
  summary:
    "The participant preferred knowing their notes were saved locally and said they would " +
    "trust the fully offline approach more on jobs with unreliable signal.",
  positiveSignal: "Liked that nothing depended on having signal at the job site.",
  objection: "Worried about forgetting to open the app again to trigger the sync.",
};

export const HUMAN_FEEDBACK_EDITED_SUMMARY =
  "Updated after a second conversation: the participant also said they'd want a visible " +
  "queue of unsynced visits so they can double check nothing was lost.";
