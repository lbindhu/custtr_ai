# AMD Vitis GitHub Tutorial Knowledge Base

This file is a **primary knowledge base** for generating Vitis-related lab documents.
When the lab topic is Vitis-related, read this file BEFORE drafting any content.
Use the exact commands, flows, prerequisites, and expected outputs documented here —
do not reconstruct them from training data.

---

## Quick Reference: Which Repo to Use

| Lab Topic | Use This Repo |
|---|---|
| HLS kernel development, pragmas, AXI interfaces | Vitis-HLS-Introductory-Examples |
| AI Engine programming, graph API, Versal | xup_aie_training + Vitis-Tutorials (AIE section) |
| ML inference, quantization, DPU deployment | Vitis-AI-Tutorials |
| FPGA acceleration, host code, XRT, Alveo | xup_compute_acceleration |
| Embedded Vitis IDE, BSP, bare-metal, Linux | Vitis-Tutorials (Embedded section) |
| Platform creation, PetaLinux, DFX | Vitis-Tutorials (Platform section) |
| General Vitis intro / all flows | Vitis-Tutorials (Getting_Started) |
| AWS F1 cloud acceleration | Vitis-AWS-F1-Developer-Labs |

---

## 1. Vitis-Tutorials (Main Repo)

**URL:** https://github.com/Xilinx/Vitis-Tutorials  
**Versions:** branches `2024.1`, `2025.1`, `2025.2` — always match the branch to the lab version

### What it covers
All major Vitis flows: AI Engine (AIE/AIE-ML/AIE-MLv2), HLS, System Design, Embedded Software,
Platform Creation, and hardware acceleration.

### Prerequisites (from repo)
- Vitis Unified Software Platform (latest: 2025.2)
- Target hardware: MPSoC (ZCU102, ZCU104), Versal (VCK190, VEK280, VEK385), Alveo cards
- Git, C/C++/Python programming knowledge

### Key setup commands
```bash
git clone https://github.com/Xilinx/Vitis-Tutorials.git
git checkout 2025.2    # replace with target version branch
```

### Tutorials available by sub-directory

| Sub-directory | Topics |
|---|---|
| `Getting_Started/` | Vitis intro, HLS intro, Libraries intro, Platform intro |
| `AI_Engine_Development/` | AIE kernel programming, GMIO, RTP, packet switching, FFT, LeNet, Softmax, Radio-ML |
| `Hardware_Acceleration/` | RTL/HLS kernel development, host code, profiling with Vitis Analyzer |
| `Embedded_Software_Development/` | Vitis IDE, user-managed mode, debugging, version control, migration from classic IDE |
| `Vitis_Platform_Creation/` | Custom MPSoC/Versal platforms, PetaLinux customization, DFX flows |
| `Vitis_System_Design/` | Functional/subsystem simulation, Versal thin platforms, AI edge designs |

---

## 2. Vitis-HLS-Introductory-Examples

**URL:** https://github.com/Xilinx/Vitis-HLS-Introductory-Examples

### What it covers
C/C++ HLS synthesis to RTL. Covers coding styles, optimization directives, interface
protocols, and co-simulation. Suitable for intermediate-level HLS labs.

### Prerequisites (from repo)
- Vitis Unified IDE 2024.x or later
- C/C++ compiler
- Python 3.6+ (for Python-based examples)
- Basic understanding of HLS concepts

### Key commands
```bash
# Run using TCL script
vitis-run --mode hls --tcl run_hls.tcl

# Run using Python script
vitis -s run.py
```

### Standard HLS flow (all examples follow this sequence)
1. C Simulation
2. C Synthesis
3. Co-Simulation

### Topics and examples available

| Category | Examples |
|---|---|
| DSP | DSP intrinsics, FFT, FIR decimator |
| Arrays | Partitioning: complete, block, cyclic, block-cyclic |
| Interfaces | AXI Master, AXI-Lite, AXI-Stream with side-channel data |
| Modeling | Arbitrary precision arithmetic, vectors, stencil operations, variable bounds |
| Pipelining | Hierarchical functions, loop pipelining |
| Task-Level Parallelism | Stream of blocks, autorestart, unique task regions, directionio |
| RTL Integration | RTL blackbox flow |
| Migration | TCL/Python migration scripts for Vitis Unified IDE |

---

## 3. Vitis-AI-Tutorials

**URL:** https://github.com/Xilinx/Vitis-AI-Tutorials  
**Versioned branches:** `2.0`, `3.5` — match the branch to the target Vitis AI version

### What it covers
End-to-end ML inference acceleration: model training, INT8/BF16 quantization,
compilation, and deployment to DPU on Zynq, Versal NPU, and Alveo targets.

### Prerequisites (from repo)
- Vitis AI version 5.1, 3.5, 3.0, 2.5, 2.0, 1.4, or 1.3 (version-dependent)
- ML frameworks: TensorFlow 2.x, PyTorch, Keras, or Caffe
- Target boards: ZCU102/104, VCK190, VEK280, Alveo V70/U50/U250, KV260
- Python environment with ML libraries

### Standard Vitis AI flow (always this sequence)
```
Train model → Quantize → Compile → Deploy to target
```

### Key commands (framework-dependent)
```bash
# TensorFlow quantization
vai_q_tensorflow

# TensorFlow compilation
vai_c_tensorflow

# PyTorch quantization (via Docker)
vai_q_pytorch
```

### Tutorials available

| Tutorial | Topic |
|---|---|
| Mixed Precision | YOLOX INT8/BF16 quantization |
| Multi-Tenancy | ResNet50 + ResNet18 temporal/spatial execution |
| NPU Deployment | Custom ResNet18, YOLOv5s on VEK280 |
| CNN Classification | ResNet18, DenseNetX, GoogleNet |
| Object Detection | YOLOv4, YOLOv5s, SSD (Caffe) |
| Semantic Segmentation | FCN8, UNET, ENet, ESPNet |
| Model Training | MNIST classification, DenseNetX, RF modulation recognition |
| Post-processing | LIDAR + Camera fusion on KV260 |
| Profiling | Vitis AI profiler introduction |

---

## 4. xup_compute_acceleration (University Program)

**URL:** https://github.com/Xilinx/xup_compute_acceleration

### What it covers
Vitis unified platform for FPGA compute acceleration. Covers OpenCL/C/C++ kernel
development, hardware/software emulation, performance optimization, and deployment
to Alveo cards and AWS F1.

### Prerequisites (from repo)
- Vitis 2021.1
- XRT 2.11.0+
- AWS F1 f1.2xlarge instance **or** Alveo U200/U250 board
- C/C++ programming knowledge

### Key commands
```bash
git clone git@github.com:Xilinx/xup_compute_acceleration.git

# Software emulation
v++ -t sw_emu -f <platform>

# Hardware emulation
v++ -t hw_emu -f <platform>

# Hardware build (full compile)
v++ -t hw -f <platform>

# Run on hardware
./host.exe a.xclbin
```

### Labs available (in order — use this sequence for a multi-step lab)

| Lab | Topic |
|---|---|
| Vitis Introduction Part 1 | GUI project creation, vector addition, software emulation |
| Vitis Introduction Part 2 | Hardware emulation, profiling, AWS F1 and on-premise hardware deployment |
| Improving Performance | Bandwidth optimization, multi-bank memory |
| Optimization | Report analysis, DATAFLOW/PIPELINING, throughput improvement |
| Vision Lab | Image resize and blur kernels using Vitis Accelerated Libraries |
| PYNQ Labs | Xilinx platform usage via PYNQ |
| RTL Kernel | RTL-to-Vitis kernel wrapper |
| Hardware Debugging | Host/kernel debug, hardware profiling |
| Streaming | Streaming interface kernels |

---

## 5. xup_aie_training (AI Engine Programming)

**URL:** https://github.com/Xilinx/xup_aie_training

### What it covers
Hands-on AI Engine kernel programming using Vitis. Covers graph API, scalar and
floating-point operations, dataflow, DSP library integration, and vector operations.
Targeted at advanced users building AIE kernels on Versal.

### Prerequisites (from repo)
- Vitis 2022.2 or later
- XRT 2.14.354 or later
- VCK5000 board **or** AWS EC2 F1 / VMAccel cloud instance
- C/C++ programming experience

### Key setup commands
```bash
git clone https://github.com/Xilinx/xup_aie_training.git
cd $HOME/xup_aie_training
# Lab-specific compilation steps follow AIE design flow
```

### Labs available

| Lab | Topic |
|---|---|
| Lab 1 | Vector addition using streams — basic AIE stream-based operations |
| Lab 2 | Matrix multiply with multiple kernels — multi-kernel AIE designs, data type support |
| Lab 3 | DSP library lab — DSP function integration and optimization |

---

## 6. Additional Repos

| Repo | URL | Best used for |
|---|---|---|
| Vitis_Accel_Examples | https://github.com/Xilinx/Vitis_Accel_Examples | Copying verified host/kernel code snippets for acceleration labs |
| Vitis_Libraries | https://github.com/Xilinx/Vitis_Libraries | Labs using math, DSP, vision, or codec Vitis libraries |
| Vitis-AWS-F1-Developer-Labs | https://github.com/Xilinx/Vitis-AWS-F1-Developer-Labs | AWS F1 cloud FPGA acceleration labs |
| Vitis-AI (main stack) | https://github.com/Xilinx/Vitis-AI | Docker setup, model zoo, DPU IP, board support packages |
| xup_embedded_system_design_flow | https://github.com/Xilinx/xup_embedded_system_design_flow | Vivado block design + Vitis IDE embedded labs |

---

## Rules for using this knowledge base

1. **Copy commands verbatim** — do not rephrase or reconstruct CLI commands from memory.
2. **Match the version** — always specify the correct branch (e.g., `2025.2`) and verify it
   matches the lab's target tool version.
3. **Mirror the tutorial sequence** — if a repo lab covers the same flow, the generated lab
   steps should follow the same order. The `.docm` is a formatted, classroom-ready version of
   that content, not a reimagined version.
4. **Cite the source** — include the repo URL in the `reference` field of the troubleshooting
   section and name it in the Step 6 confirmation to the user.
5. **If a command or expected output is not in this file**, query Nabu or use WebFetch on the
   specific GitHub page before inventing anything.
