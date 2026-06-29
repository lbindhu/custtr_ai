# Lab Document Image Database

Place any images you want to embed in lab documents here.

## How to add images

1. Save the image file (PNG or JPG) into this folder
2. Reference it in `lab_config.json` using the `image` key:

```json
{"image": "vivado_platform_setup.png", "caption": "Figure showing Platform Setup tab in Vivado"}
```

The caption is optional. If omitted, no caption is printed below the image.

## Naming convention (recommended)

Use lowercase with underscores. Include the tool or step context so files are easy to find:

```
vivado_block_design.png
vitis_platform_flow.png
aie_graph_topology.png
general_flow_diagram.png
```

## Image sizing

Images are automatically scaled to fit within the page content width (5.5 inches max).
Aspect ratio is preserved. Best source resolution: 1200–1920 px wide at 96 DPI.

## Supported formats

- PNG  (.png)
- JPEG (.jpg / .jpeg)
