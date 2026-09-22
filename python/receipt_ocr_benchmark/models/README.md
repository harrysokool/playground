# Local PaddleOCR Models

PaddleOCR is configured to load models from local directories here instead of downloading
them, so the benchmark runs fully offline (needed on the Azure VM, which has no internet
access to the model hosters).

Expected structure — each is an extracted PaddleOCR/PaddleX inference model archive
(containing `inference.json`, `inference.pdiparams`, `inference.yml`, etc.):

```
models/
├── PP-OCRv5_mobile_det_infer/   # used by configs/paddle_light.yaml
├── PP-OCRv5_mobile_rec_infer/   # used by configs/paddle_light.yaml
├── PP-OCRv5_server_det_infer/   # used by configs/paddle_heavy.yaml
└── PP-OCRv5_server_rec_infer/   # used by configs/paddle_heavy.yaml
```

These are large binary archives and are not committed to Git (see `.gitignore`) — each
machine running the benchmark needs its own copy under `models/`.
