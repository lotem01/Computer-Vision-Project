# PoseLab

PoseLab is a local, presentation-ready pose-to-avatar studio. It preloads four Ultralytics pose models, supports camera/image/video input, draws a normalized skeleton, and renders a replaceable avatar output.

## Run locally

Requirements: Node.js 20+, npm, and Python 3.9+ (the setup script prefers the installed Python 3.9 runtime for PyTorch compatibility).

```powershell
.\setup.ps1
.\start.ps1
```

Open `http://127.0.0.1:8000`. The readiness screen shows real model loading and warm-up status. Failed models are disabled without blocking the remaining studio.

## Architecture

- `backend/app/domain`: versioned data contracts and implementation protocols.
- `backend/app/models`: Ultralytics adapter, model registry, and keypoint normalization.
- `backend/app/renderers`: fast local avatar and optional notebook-derived diffusion renderer.
- `backend/app/media`: image/media encoding boundary.
- `backend/app/services`: inference and video application workflows.
- `backend/app/infrastructure`: replaceable in-memory video job store.
- `frontend/src/features`: independent readiness, model, camera, upload, and result modules.
- `frontend/src/api`: the only frontend layer that knows HTTP/WebSocket details.
- `reference`: original research notebook retained unchanged.

## Common changes

### Add or change a model

Edit `backend/app/config.py`. Add one `ModelDefinition` with its weight path, ordered joint names, and skeleton edges. No API or UI changes are required.

### Change the 13-joint mapping

Update `CANONICAL_13` and `BODY_13_EDGES` in `backend/app/config.py`. The normalizer and every input mode use this configuration automatically.

### Replace the avatar

Implement the `AvatarRenderer` protocol in `backend/app/domain/protocols.py`, then inject it into `InferenceService`. A renderer receives the source frame, normalized named keypoints, and configured edges; it does not depend on Ultralytics.

### Change the visual identity

Design tokens are at the top of `frontend/src/styles/global.css`. Feature components use those tokens rather than hard-coded themes.

### Enable diffusion

On a CUDA computer, install `backend/requirements-diffusion.txt` and set `POSEAPP_ENABLE_DIFFUSION=1`. The main studio never waits for diffusion and remains usable if it is unavailable.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
Set-Location frontend
npm test
npm run build
```
