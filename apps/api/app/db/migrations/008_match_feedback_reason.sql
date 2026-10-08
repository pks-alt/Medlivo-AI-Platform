ALTER TABLE match_feedback
  ADD COLUMN IF NOT EXISTS reason_code text;

ALTER TABLE match_feedback
  DROP CONSTRAINT IF EXISTS match_feedback_reason_code_check;

ALTER TABLE match_feedback
  ADD CONSTRAINT match_feedback_reason_code_check
  CHECK (
    reason_code IS NULL OR reason_code IN (
      'license',
      'certification',
      'specialty',
      'care_setting',
      'experience',
      'availability',
      'location',
      'compensation',
      'other'
    )
  );
