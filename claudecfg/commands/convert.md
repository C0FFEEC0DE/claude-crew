# /convert

Convert model to another format.

## When to use
- Safetensors → GGUF
- BF16 → INT4/INT8
- Export for Ollama

## Tools
- llama.cpp (convert, quantize)
- export/convert_to_gguf.py

## Formats
- GGUF (for llama.cpp, Ollama)
- ONNX (for inference)
- Safetensors (HuggingFace)