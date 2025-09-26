"""Export helpers for ONNX/TensorRT deployment."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch


def export_onnx(model: torch.nn.Module, sample_inputs: torch.Tensor, output_path: Path, opset: int = 17) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        sample_inputs,
        output_path.as_posix(),
        export_params=True,
        opset_version=opset,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["embeddings"],
        dynamic_axes={"input": {0: "batch"}, "embeddings": {0: "batch"}},
    )
    return output_path


def build_tensorrt_engine(onnx_path: Path, engine_path: Path, fp16: bool = True) -> Optional[Path]:
    try:
        import tensorrt as trt  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        return None

    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    network = builder.create_network(network_flags)
    parser = trt.OnnxParser(network, logger)

    with open(onnx_path, "rb") as fp:
        if not parser.parse(fp.read()):
            errors = [parser.get_error(i) for i in range(parser.num_errors)]
            raise RuntimeError(f"Failed to parse ONNX graph: {errors}")

    config = builder.create_builder_config()
    if fp16:
        config.set_flag(trt.BuilderFlag.FP16)

    engine = builder.build_engine(network, config)
    if engine is None:
        raise RuntimeError("TensorRT engine build failed")

    engine_path.parent.mkdir(parents=True, exist_ok=True)
    with open(engine_path, "wb") as fp:
        fp.write(engine.serialize())
    return engine_path
