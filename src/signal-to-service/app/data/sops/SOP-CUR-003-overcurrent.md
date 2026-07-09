---
sop_id: SOP-CUR-003
title: Motor overcurrent and drive fault — conveyors and gearmotors
failure_mode: overcurrent
required_skill: electrical
revision: 1.8
---

# SOP-CUR-003 · Motor overcurrent / drive fault

## Applicability
Applies to conveyor gearmotors and VFD-driven motors where line current climbs
above the warning threshold, often with rising temperature. Root causes include
mechanical binding, misalignment, overload, phase imbalance or a failing VFD.

## Safety
1. LOTO the drive and verify zero energy at the motor terminals.
2. Discharge the VFD DC bus and wait the rated capacitor discharge time.
3. Use a CAT III meter for all live measurements.

## Diagnosis confirmation
1. Measure per-phase current; check imbalance is under 5 %.
2. Rotate the load by hand to detect binding or jammed product.
3. Inspect the gearbox oil level and condition.
4. Read the VFD fault log for overcurrent/overtemperature codes.

## Corrective procedure
1. Clear any mechanical jam and free the conveyor path.
2. Correct coupling/belt misalignment; re-tension to spec.
3. Replace worn gearbox bearings or top up/replace oil as needed.
4. Rebalance phases; tighten loose terminals; replace damaged cabling.
5. If the VFD is faulted, reset and, if it recurs, replace the drive.

## Post-repair verification
1. Run under normal load; confirm current returns below the warning limit.
2. Confirm phase balance and log readings in the work order.
