-- Scheduled follow-up execution links sequence steps to the normal human-reviewed outreach flow.
ALTER TABLE public.ws_outreach_draft
  ADD COLUMN IF NOT EXISTS followup_sequence_id uuid,
  ADD COLUMN IF NOT EXISTS followup_sequence_step_id uuid;

ALTER TABLE public.ws_outreach_draft
  ADD CONSTRAINT ws_outreach_draft_followup_sequence_fk
    FOREIGN KEY (followup_sequence_id) REFERENCES public.ws_followup_sequence(id);

ALTER TABLE public.ws_outreach_draft
  ADD CONSTRAINT ws_outreach_draft_followup_step_fk
    FOREIGN KEY (followup_sequence_step_id) REFERENCES public.ws_followup_sequence_step(id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_outreach_draft_followup_step
  ON public.ws_outreach_draft (followup_sequence_step_id)
  WHERE followup_sequence_step_id IS NOT NULL;
