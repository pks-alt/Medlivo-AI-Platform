-- Governed company economics and customer/MSP overrides.
-- Apply after 010_margin_snapshots.sql.

CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_customer_tenant_id
  ON public.customer(tenant_id, id);

CREATE TABLE IF NOT EXISTS public.ws_customer_economic_rule (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  customer_id uuid NOT NULL,
  calculation_profile text NOT NULL,
  version text NOT NULL,
  rule_payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'active',
  effective_from timestamptz NOT NULL,
  effective_to timestamptz,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_customer_economic_rule_customer_fk FOREIGN KEY (tenant_id, customer_id)
    REFERENCES public.customer(tenant_id, id),
  CONSTRAINT ws_customer_economic_rule_user_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_customer_economic_rule_status_ck CHECK (status IN ('active','retired')),
  CONSTRAINT ws_customer_economic_rule_uq UNIQUE (
    tenant_id, customer_id, calculation_profile, version
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_customer_economic_rule_effective
  ON public.ws_customer_economic_rule(
    tenant_id, customer_id, calculation_profile, effective_from DESC
  );

ALTER TABLE public.ws_margin_snapshot
  ADD COLUMN IF NOT EXISTS customer_rule_id uuid,
  ADD COLUMN IF NOT EXISTS customer_rule_version text;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='ws_margin_snapshot_customer_rule_fk'
  ) THEN
    ALTER TABLE public.ws_margin_snapshot
      ADD CONSTRAINT ws_margin_snapshot_customer_rule_fk
      FOREIGN KEY (customer_rule_id) REFERENCES public.ws_customer_economic_rule(id);
  END IF;
END
$$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_cost_assumption_set TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_customer_economic_rule TO medlivo_team_api_runtime';
  END IF;
END
$$;
