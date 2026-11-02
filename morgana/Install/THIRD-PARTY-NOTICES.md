# Third-party notices - Morgana distribution

Morgana Server itself is Copyright (C) 2026 X3M.AI Ltd (UK) - Nino Crudele.
See the LICENSE file in the Morgana repository.

The files in this folder redistribute the following third-party components.

## AI runtime archive - morgana-ai-runtime-0.3.35.zip

Optional. Only needed if you install the local AI Pack. Not required for the
core product.

| Component | Version | Licence | Upstream |
|-----------|---------|---------|----------|
| llama-cpp-python | 0.3.35 | MIT | https://github.com/abetlen/llama-cpp-python |
| llama.cpp (llama.dll, ggml*.dll, mtmd.dll) | bundled with llama-cpp-python 0.3.35 | MIT | https://github.com/ggml-org/llama.cpp |
| Jinja2 | 3.1.6 | BSD-3-Clause | https://palletsprojects.com/p/jinja/ |
| diskcache | 5.6.3 | Apache-2.0 | https://github.com/grantjenks/python-diskcache |
| typing_extensions | bundled | PSF-2.0 | https://github.com/python/typing_extensions |

numpy is NOT included in the runtime archive. It is provided by the Morgana
Server distribution itself (numpy is BSD-3-Clause).

## Local AI Pack model weights - Qwen3.5-4B

The model weights are NOT part of this folder and NOT part of the installer.
They are downloaded on demand when you install the AI Pack, from the pinned
upstream location recorded in the AI Pack catalog.

| Item | Value |
|------|-------|
| Base model | Qwen/Qwen3.5-4B |
| GGUF publisher | unsloth/Qwen3.5-4B-GGUF |
| Revision | e87f176479d0855a907a41277aca2f8ee7a09523 |
| File | Qwen3.5-4B-Q4_K_M.gguf |
| Licence | Apache-2.0 |
| Upstream licence | https://huggingface.co/Qwen/Qwen3.5-4B/blob/main/LICENSE |

Qwen3.5-4B is a pretrained model by the Qwen team (Alibaba). The GGUF
quantization is published by unsloth. X3M.AI integrates the upstream pretrained
weights; X3M.AI did not train this model.

## Morgana Agent (morgana-agent.exe)

Built with the Go standard library plus the following modules. Their licence
texts are reproduced in the Morgana repository under agent/go.sum and the
corresponding module licences.

The agent is delivered by the server at /download/morgana-agent.exe and is not
shipped as a separate file in this folder.

## Python runtime (embedded in morgana-server.exe)

PSF-2.0. Bundled by PyInstaller together with the core Morgana dependencies,
whose licences are listed in the Morgana repository.
