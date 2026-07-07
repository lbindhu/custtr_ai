---
name: upgrade-build-and-validation
description: 'Sub-skill for running the upgraded design through synthesis, implementation, and device image generation with full timing closure validation.'
argument-hint: 'Provide the upgraded project path from sub-skill 2'
applyTo: '**'
---

# Sub-Skill 3: Build and Validation (Synthesis, Implementation, Device Image Generation)

Handles running the fully upgraded design through the complete Vivado build flow: synthesis, implementation (place-and-route), timing closure, and device image (bitstream/PDI) generation.

## When to Use

- After Sub-Skill 2 has applied the upgrade and passed initial validation (elaboration + IP generation)
- Ready to produce a final synthesized/implemented design
- Need to verify timing closure on the upgraded design
- Need to generate a programming file (bitstream or PDI)

## Prerequisites

- Sub-Skill 2 completed: upgraded project passes elaboration and IP generation
- All IPs upgraded and targets generated
- Constraints files updated for any clock/pin changes
- Target Vivado version open with the upgraded project loaded

## Procedure

### Phase 6: Full Design Build

1. **Run Synthesis** — Launch synthesis with appropriate job parallelism:
    ```tcl
    reset_runs synth_1
    launch_runs synth_1 -jobs 8
    wait_on_runs synth_1
    ```
    - Check for CRITICAL WARNINGS or ERRORS in the synthesis log
    - Review `synth_1/runme.log` for any IP-related issues
    - If synthesis fails, analyze the error and fix before proceeding

2. **Open Synthesized Design and Review** — Verify synthesis results:
    ```tcl
    open_run synth_1
    report_utilization -file utilization_synth.rpt
    report_timing_summary -file timing_synth_summary.rpt
    report_methodology -file methodology.rpt
    ```
    - Check for timing violations at the synthesis stage
    - Review methodology report for design rule violations
    - Compare utilization against expected resource usage

3. **Run Implementation** — Launch place-and-route:
    ```tcl
    reset_runs impl_1
    launch_runs impl_1 -jobs 8
    wait_on_runs impl_1
    ```
    - Monitor for placement or routing failures
    - If implementation fails, consider:
      - Adjusting implementation strategy (e.g., `Performance_HighUtilSLRs`)
      - Adding/modifying floorplan constraints
      - Relaxing timing constraints if appropriate

4. **Open Implemented Design and Verify Timing** — Ensure timing closure:
    ```tcl
    open_run impl_1
    report_timing_summary -file timing_impl_summary.rpt
    report_utilization -hierarchical -file utilization_impl.rpt
    report_power -file power.rpt
    report_route_status -file route_status.rpt
    ```
    - Verify all timing constraints are met (no setup/hold violations)
    - Check for unrouted nets in route status report
    - Review power estimate for reasonableness

5. **Generate Device Image (Bitstream/PDI)** — Produce the final programming file:
    ```tcl
    # For Versal devices (PDI - Programmable Device Image):
    launch_runs impl_1 -to_step write_device_image -jobs 8
    wait_on_runs impl_1

    # For UltraScale+/7-Series devices (Bitstream):
    # launch_runs impl_1 -to_step write_bitstream -jobs 8
    # wait_on_runs impl_1
    ```
    - Verify the output file is generated:
      - Versal: `*.pdi` in the impl_1 directory
      - UltraScale+/7-Series: `*.bit` in the impl_1 directory
    - Check for any DRC errors during device image generation

6. **Post-Build Validation** — Final checks after successful build:
    ```tcl
    report_utilization -file final_utilization.rpt
    report_timing_summary -max_paths 10 -file final_timing.rpt
    report_clock_utilization -file clock_utilization.rpt
    ```
    - Confirm zero timing violations (WNS ≥ 0, WHS ≥ 0)
    - Verify no CRITICAL WARNINGS in the implementation log
    - Archive the device image and reports for deployment

7. **Compare with Original Design** — Validate equivalence:
    - Compare utilization reports (old vs. upgraded) to catch unexpected resource changes
    - Verify timing results are comparable or improved
    - Document any resource differences with justification

8. **Build Summary** — Document the build results:
    - Record synthesis/implementation runtime
    - Note any strategy changes required for timing closure
    - Document resource utilization (LUTs, FFs, BRAMs, DSPs, GT channels)
    - Record worst negative slack (WNS) and worst hold slack (WHS)
    - Note the device image file location and size

## Output Artifacts

- Synthesis utilization and timing reports
- Implementation utilization, timing, power, and route status reports
- Device image file (`.bit` or `.pdi`)
- Utilization comparison report (old vs. upgraded)
- Final build summary with all metrics
- Clock utilization report

## Key Principles

- **Timing closure is mandatory** — Do not deliver a design with setup or hold violations
- **Compare old vs. new** — Unexpected utilization changes may indicate incorrect connections
- **Strategy iteration** — If timing fails, try different implementation strategies before modifying RTL
- **Check route status** — Unrouted nets indicate incomplete implementation
- **Document everything** — Record runtime, strategy, and all key metrics for reproducibility

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Synthesis fails with IP errors | Return to Sub-Skill 2, regenerate IP targets |
| Timing violations (WNS < 0) | Try aggressive implementation strategy, add pipelining, or relax constraints |
| Placement failures | Check for over-constrained floorplan, reduce LOC constraints |
| Routing congestion | Enable `PhysOpt` steps, consider design restructuring |
| DRC errors during bitstream | Fix constraint violations reported in DRC |
| Unexpected resource increase | Verify IP configuration matches original intent |
