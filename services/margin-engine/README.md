# Medlivo Margin Engine\n\nPhase 1 versioned calculation service for projected staffing economics. See `docs/PHASE1_MARGIN_COST_ENGINE.md`.\n
## W-2 pay package rules

`w2_pay_package.py` translates recruiter-facing Nursing/Allied and Rehabilitation package inputs into governed weekly billing, taxable wages, stipends, orientation cost and other one-time costs. California daily/weekly OT and double-time are calculated automatically from the approved workbook rules. National standard OT and the approved 48-Regular/No-OT option remain explicit policy choices.
