# Design files

Body of the climber (wheels, hoop frames, H-frame chassis). Electronics are not modelled; see [docs/BUILD.md](../docs/BUILD.md) for where they mount.

![render](assets/robot_preview.png)

| File | What |
|---|---|
| `blender/build_robot.py` | Builds everything below + `sim/meshes/*.stl`, then runs the hoop clearance check |
| `assets/wall_climber_body.blend` | Blender model |
| `assets/wall_climber_body.glb` | Same model for any 3D viewer |
| `assets/robot_preview.png` | Render |

Rebuild from the repo root (Blender 4.2+):

```bash
blender -b --factory-startup -P design/blender/build_robot.py
```

It must print `CLEARANCE OK`. Each hoop sweeps a 130 mm ball around its pivot when it tilts (−40…140°).
`CLEARANCE FAIL` means a frame part is inside that ball, and the real hoop would hit it.
If you change a dimension here, change it in `sim/wall_climber.xml` too.
