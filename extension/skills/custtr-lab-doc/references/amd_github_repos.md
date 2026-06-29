# AMD Lab Document Generation — GitHub Repository Knowledge Base

**Generated:** 2026-05-28  
**Purpose:** Reference for AMD lab document generation skill — maps XUP GitHub repositories to lab content, boards, tool versions, and AMD training topics.

---

## Quick Reference: Which Repo to Use

| Lab Topic | Repository | URL |
|---|---|---|
| Vivado FPGA design flow, synthesis, ILA debug | xup_fpga_vivado_flow | https://github.com/Xilinx/xup_fpga_vivado_flow |
| Advanced Vivado, Versal NoC, DFX, device architecture | Vivado-Design-Tutorials | https://github.com/Xilinx/Vivado-Design-Tutorials |
| Embedded Zynq PS/PL design, Vitis, custom IP, boot | xup_embedded_system_design_flow | https://github.com/Xilinx/xup_embedded_system_design_flow |
| HLS C-to-RTL synthesis, optimization directives | xup_high_level_synthesis_design_flow | https://github.com/Xilinx/xup_high_level_synthesis_design_flow |
| Formal embedded tutorials (UG1165/UG1209), Zynq-7000, ZynqMP, Versal | Embedded-Design-Tutorials | https://github.com/Xilinx/Embedded-Design-Tutorials |
| Vitis AI Engine, HLS, acceleration, platform creation | Vitis-Tutorials | https://github.com/Xilinx/Vitis-Tutorials |

---

## Repository 1: xup_fpga_vivado_flow

**URL:** https://github.com/Xilinx/xup_fpga_vivado_flow  
**Docs:** https://xilinx.github.io/xup_fpga_vivado_flow/  
**AMD Training Topic:** Vivado Design Suite (DS) — F1/F2/F3 courses; synthesis, implementation, constraints, hardware debug  
**Clone:**
```bash
git clone https://github.com/Xilinx/xup_fpga_vivado_flow
```
**Boards:** Boolean (Spartan-7 XC7S50), PYNQ-Z2 (Zynq XC7Z020)  
**Vivado Version:** 2021.2

### Labs
| Lab | Title | Key Content |
|---|---|---|
| Lab 1 | Vivado Design Flow | Create project, simulate, synthesize, implement, bitstream, download |
| Lab 2 | Synthesizing an RTL Design | Synthesis settings, flatten_hierarchy, design analysis, reports |
| Lab 3 | Implementing the Design | Static timing analysis, implement, generate bitstream |
| Lab 4 | IP Catalog and IP Integrator | Clock IP, FIFO via IPI, PS GPIO/EMIO pass-through for UART |
| Lab 5 | Xilinx Design Constraints (XDC) | I/O Planning, assign pins via Device view and Tcl |
| Lab 6 | Hardware Debugging (ILA) | Mark Debug, ILA from IP Catalog, synthesize, implement, debug |

### Lab 6 — ILA Debug Detail
- ILA component name: `ila_led` — 2 probes: PROBE0 width=1 (`rx_data_rdy_out`), PROBE1 width=8 (LEDs)
- Trigger: `rx_data_rdy_out == [B] 1`, position 512
- Two ILA cores: `hw_ila_1` (instantiated) and `hw_ila_2` (Mark Debug)
- TCL script: `ps_init.tcl` — generates PS block design (`system.bd`) for PYNQ-Z2

### Key Source Files
- `uart_led.v`, `uart_rx.v`, `led_ctl.v`, `meta_harden.v`, `uart_baud_gen.v`, `uart_rx_ctl.v`
- Top-level: `uart_led` (PYNQ-Z2), `uart_top` (Boolean)
- Constraints: `uart_led_timing_{BOARD}.xdc`, `uart_led_pins_{BOARD}.xdc`
- BAUD_RATE: 115200 | CLOCK_RATE: 125 MHz (PYNQ-Z2), 100 MHz (Boolean)

---

## Repository 2: Vivado-Design-Tutorials

**URL:** https://github.com/Xilinx/Vivado-Design-Tutorials  
**AMD Training Topic:** Advanced Vivado — Versal NoC, DFX, boot, IO design, UltraScale+ device architecture  
**Clone (version-specific branch):**
```bash
git clone -b 2024.2 https://github.com/Xilinx/Vivado-Design-Tutorials
```
**Boards:** VCK190, VMK180, ZCU102, custom PCB  
**Vivado Versions:** Branched by year: 2021.1 → 2025.2 (each tutorial tagged to validated version)

### Key Tutorial Areas
| Area | Topics |
|---|---|
| Versal NoC & DDRMC | XPM macros, QoS, AXI traffic generators, simulation performance |
| Versal NoC & HBMC | High Bandwidth Memory Controller design |
| DFX | Block Design Container, multiple RPs, clock sharing, JTAG/HSDP debug, NoC connectivity |
| Boot & Config | JTAG boot mode on VCK190 |
| PCB Design | Memory pinouts, Advanced I/O Wizard (AIOW), XPHY, XPLL |

### Key Reference Docs
UG949 (UltraFast Methodology), UG583 (PCB Design), UG899 (I/O Planning), UG907 (Power), UG835 (Tcl Reference), UG940 (Embedded HW Tutorial)

---

## Repository 3: xup_embedded_system_design_flow

**URL:** https://github.com/Xilinx/xup_embedded_system_design_flow  
**Docs:** https://xilinx.github.io/xup_embedded_system_design_flow/  
**AMD Training Topic:** Embedded System Design on Zynq — PS/PL co-design, AXI IP, Vitis, boot  
**Clone:**
```bash
git clone https://github.com/Xilinx/xup_embedded_system_design_flow
```
**Boards:** PYNQ-Z2 (primary), ZedBoard, Zybo  
**Vivado + Vitis Version:** 2021.2

### Labs
| Lab | Title | Key Content |
|---|---|---|
| Lab 1 | Build an Embedded System | Zynq project, IPI, export XSA, Vitis memory test, run on board |
| Lab 2 | Adding IP Cores in PL | Two GPIO IPs, AXI Master GP0 interface, external FPGA I/O |
| Lab 3 | Adding Custom IP in PL | IP Packager, custom AXI peripheral, BRAM Controller, bitstream |
| Lab 4 | Basic Software Application | LED app in Vitis, BRAM linker script, verify on hardware |
| Lab 5 | CPU Private Timer Application | Timer API, dip switch monitor, LED count, software debug |
| Lab 6 | Hardware/Software Debugging | Vitis System Debugger, hardware analyzer debug cores, ILA in PL |
| Lab 7/8 | Configuration and Booting | Bootable image (SD/QSPI), Create Boot Image wizard, .bin format |

### Key Outputs
- `.xsa` (Xilinx Support Archive) — exported from Vivado, imported into Vitis

---

## Repository 4: xup_high_level_synthesis_design_flow

**URL:** https://github.com/Xilinx/xup_high_level_synthesis_design_flow  
**Docs:** https://xilinx.github.io/xup_high_level_synthesis_design_flow/  
**AMD Training Topic:** High-Level Synthesis (HLS) — C-to-RTL, optimization, system integration, PYNQ deployment  
**Clone:**
```bash
git clone https://github.com/Xilinx/xup_high_level_synthesis_design_flow
```
**Boards:** PYNQ-Z2, PYNQ-ZU, KV260  
**Vitis HLS Version:** 2021.2 (basic labs), 2023.2 (environment setup)

### Labs
| Lab | Title | Key Content |
|---|---|---|
| Lab 1 | Vitis HLS Design Flow | Create HLS project, simulate, synthesize, implement; matmul; TRIPCOUNT pragma |
| Lab 2 | Improving Performance | RGB-to-YUV conversion; loop pipelining; TRIPCOUNT directive |
| Lab 3 | Improving Area | DCT on 8x8 block; pipelining + inlining; latency: 5990→2451 cycles |
| Lab 4 | System Integration (FIR) | FIR HLS IP, Vivado IPI, ZynqMP system, ARM + FIR, software app |
| PBL-FIR | FIR Filter (Bird Sound) | C++ FIR in HLS, AXI4 data transfer, PYNQ hardware acceleration |
| PBL-Sobel | Sobel with Vitis Vision Library | Hand-coded vs Vision Library (3× faster), PYNQ Jupyter Lab |

### Environment Setup (Linux)
```bash
export LAB_WORK_DIR=<repo>/source
source <Vitis_install>/Vitis/2023.2/settings64.sh
```

---

## Repository 5: Embedded-Design-Tutorials

**URL:** https://github.com/Xilinx/Embedded-Design-Tutorials  
**Docs:** https://xilinx.github.io/Embedded-Design-Tutorials/  
**AMD Training Topic:** Official AMD embedded tutorials — UG1165 (Zynq-7000), UG1209 (ZynqMP), Versal, MicroBlaze  
**Clone:**
```bash
git clone https://github.com/Xilinx/Embedded-Design-Tutorials
```
**Boards:** ZC702 (Zynq-7000), ZCU102 (ZynqMP), VCK190/VMK180/VPK180 (Versal)  
**Tools:** Vivado + Vitis + PetaLinux (multi-version; tutorials versioned independently)

### Introduction Tutorials
| Tutorial | Board | Key Content |
|---|---|---|
| Zynq-7000 EDT (UG1165) | ZC702 | Configure PS, Vivado hardware design, Hello World in Vitis, JTAG debug, boot devices |
| ZynqMP EDT (UG1209) | ZCU102 | Vivado + Vitis for ZynqMP, PS config, bare metal + Linux |
| Versal ACAP EDT | VCK190/VMK180/VPK180 | Versal PS/PL co-design, boot |

### Feature Tutorials
| Tutorial | Platform | Key Content |
|---|---|---|
| MicroBlaze System | Spartan-7 | Create MicroBlaze system via Vivado IPI |
| FSBL | Zynq/ZynqMP | FSBL initialization, load app/data, launch on target CPU |
| Software Profiling | Zynq/ZynqMP | Enable profiling for standalone BSP; AXI CDMA application |
| Embedded Software Debug | Zynq/ZynqMP | Debug scenarios, XSCT, System Debugger |
| Performance Analysis | ZynqMP | Performance analysis methodology |
| Dhrystone Benchmark | Zynq/ZynqMP | Reference design, build and run Dhrystone app |

### Notes
- Zynq-7000 tutorial: PetaLinux requires Linux OS; bare-metal portions run on Windows
- Chinese (docs-cn) and Japanese (docs-jp) translations available in repo

---

## Repository 6: Vitis-Tutorials (already in amd_vitis_tutorials.md)

**URL:** https://github.com/Xilinx/Vitis-Tutorials  
**Branches:** `2024.1`, `2025.1`, `2025.2` — match branch to lab version  
See `references/amd_vitis_tutorials.md` for full detail on AIE, HLS, Embedded, Platform, and Acceleration flows.

---

## Notes for Lab Generation

1. **ILA debug lab is Lab 6** in xup_fpga_vivado_flow (not Lab 5 — Lab 5 is XDC/I/O Planning)
2. **Versioned branches** — Vivado-Design-Tutorials uses Git branches per release year; always clone the matching branch
3. **PYNQ-Z2 Lab 6 TCL:** Copy `ps_init.tcl` to lab directory before execution; top module is `system_wrapper`
4. **HLS PBL labs** require PYNQ board + Jupyter Lab — not a pure Vivado/Vitis flow; note in prerequisites
5. **Embedded-Design-Tutorials** dual-OS requirement: PetaLinux on Linux, bare-metal on Windows — always flag this in prerequisites table
6. **Always clone the version branch** matching the lab's target tool version
