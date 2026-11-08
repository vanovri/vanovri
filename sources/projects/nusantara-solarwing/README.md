# Nusantara SolarWing

NusaSentinel's ISAST 2026 Track 01 concept package, led by Ardhya Novri Ramadhan. The innovation title is “Nusantara SolarWing: Wind-Aware Reserve Planning for Natuna Maritime Patrols.” It is a model-backed proposal, not a flown prototype.

## Deliverables

- `Nusantara_SolarWing_ISAST_2026_Submission.pdf`: five English concept-paper pages, references, and one appended student ID page. Keep this file private and upload it only to the intended ISAST portal.
- `Nusantara_SolarWing_ISAST_2026_Public_Brief.pdf`: the same five-page paper without the ID. This is the file linked from `index.html`.
- `SUBMISSION_FORM_DATA.md`: verified form fields, title, and 212-word abstract. The entrant must supply their email and WhatsApp number.
- `index.html`: responsive public demo with historical solar replay, route diagram, explicit dispatch thresholds, wind sensitivity, and source links.

The former concept-review PDF is in `archive_review_v1/`. The original Antigravity output is in `archive_antigravity_draft/` and includes superseded technical claims.

## Reproduce

Run `python analyze.py` to regenerate the processed NASA POWER data from the cached raw API response. Run `python build_submission_pdf.py` to regenerate both PDFs. The PDF script reads the entrant-supplied KTM from its existing local path and does not copy the card into the public website.

The historical screen uses September 2025 NASA POWER hourly all-sky surface irradiance at 4.0°N, 108.0°E shifted to WIB. Baseline assumptions: 1.65 m² PV, 24% cells, 96.5% MPPT, 147.5 W level-flight load, 894.24 Wh nominal pack, 90% launch SoC, 20% reserve, and 95% charge/discharge efficiency. Under the no-wind 08:00–16:00 screen, 29/30 days retain the reserve. This result does not include an actual route or safety approval.

The maritime case uses Ranai Airport's published reference point only as a geometric anchor. A five-leg 12 × 8 km creeping-line planning box with 2 km lane spacing has 68 km of straight search segments. A 20 km ingress and a 20 km egress give a 108 km minimum ideal route. For a 20 km return into a 5 m/s headwind, constant-power electrical energy rises from 60.7 to 96.4 Wh. With 95% battery discharge efficiency, that return debits 101.5 Wh from the pack. The illustrative decision thresholds at 20 km are return at ≤41.3% SoC, shorten between 41.3% and 45.6%, and patrol at ≥45.6%. Recompute from current position and forecast before every leg.

The matched-pack battery-only level-flight estimate is 4.03 h to the 20% reserve. The solar-assisted historical screen reaches 8 h on 29/30 days, an upper scenario of 3.97 h additional endurance. Cost and CO₂ advantages over ships or combustion aircraft are not claimed because no measured, matched comparator was available.

## Primary sources

- [NASA POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/)
- [Panasonic NCR18650GA](https://energy.panasonic.com/eu/business/products/lithium-ion/models/NCR18650GA)
- [Ranai Airport reference point, Indonesian Directorate General of Civil Aviation](https://hubud.kemenhub.go.id/bandara/297)
- [Noth, solar airplane design thesis](https://doi.org/10.3929/ethz-a-005745622)
- [IMO AIS guidance](https://www.imo.org/en/ourwork/safety/pages/ais.aspx)
- [ICCAE 2024 energy-aware solar UAV navigation](https://doi.org/10.1109/ICCAE59995.2024.10569793)
- [ISAST challenge rules](https://www.isast.space/#challenge)
