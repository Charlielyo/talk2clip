#!/usr/bin/env python3
"""convert_pt_to_ct2.py — openai-whisper .pt → faster-whisper(CT2) 模型

用法:
    python3 convert_pt_to_ct2.py /path/to/small.pt /output/dir

原理:
  1. whisper 加载 .pt，提取 state_dict（torch）
  2. 键名映射为 transformers WhisperForConditionalGeneration 格式
  3. 保存 transformers 目录 (pytorch_model.bin + config.json)
  4. 生成 tokenizer.json（从 whisper 的 tiktoken 资源）+ preprocessor_config.json
  5. 用 ctranslate2 的 TransformersConverter 转成 CT2 int8
"""
import json
import os
import sys

# openai → transformers 键名映射（WhisperForConditionalGeneration）
# 注意顺序：先长后短，避免部分替换
_SUB_MAP = [
    (".cross_attn.query", ".encoder_attn.q_proj"),
    (".cross_attn.key", ".encoder_attn.k_proj"),
    (".cross_attn.value", ".encoder_attn.v_proj"),
    (".cross_attn.out", ".encoder_attn.out_proj"),
    (".cross_attn_ln", ".encoder_attn_layer_norm"),
    (".attn.query", ".self_attn.q_proj"),
    (".attn.key", ".self_attn.k_proj"),
    (".attn.value", ".self_attn.v_proj"),
    (".attn.out", ".self_attn.out_proj"),
    (".attn_ln", ".self_attn_layer_norm"),
    (".mlp.0", ".fc1"),
    (".mlp.2", ".fc2"),
    (".mlp_ln", ".final_layer_norm"),
]

# 顶层整体改名（键前缀匹配，映射到完整目标键）
_TOP_PREFIX = [
    ("encoder.ln_post.", "model.encoder.layer_norm."),
    ("encoder.positional_embedding", "model.encoder.embed_positions.weight"),
    ("decoder.ln.", "model.decoder.layer_norm."),
    ("decoder.proj.", "proj_out."),   # transformers 下 proj_out 无 model. 前缀
    ("decoder.token_embedding.", "model.decoder.embed_tokens."),
    ("decoder.positional_embedding", "model.decoder.embed_positions.weight"),
]


def remap(state_dict):
    out = {}
    for k, v in state_dict.items():
        nk = k
        # 1) 顶层前缀改名
        for src, dst in _TOP_PREFIX:
            if nk.startswith(src):
                nk = dst + nk[len(src):]
                break
        else:
            # 2) 层内子名替换
            for src, dst in _SUB_MAP:
                nk = nk.replace(src, dst)
            # 3) 加 model. 前缀（blocks → layers 也在此转换）
            if nk.startswith("encoder."):
                nk = "model." + nk
                nk = nk.replace("encoder.blocks.", "encoder.layers.")
            elif nk.startswith("decoder."):
                nk = "model." + nk
                nk = nk.replace("decoder.blocks.", "decoder.layers.")
        out[nk] = v
    return out


def find_tiktoken_file():
    import whisper
    from pathlib import Path
    base = Path(whisper.__file__).parent / "assets"
    for name in ("multilingual.tiktoken", "gpt2.tiktoken"):
        p = base / name
        if p.exists():
            return str(p)
    raise FileNotFoundError("找不到 tiktoken 资源文件")


def make_preprocessor_json(save_path):
    data = {
        "feature_size": 80,
        "hop_length": 160,
        "chunk_length": 30,
        "n_fft": 400,
        "padding_side": "right",
        "padding_value": 0.0,
        "return_attention_mask": False,
        "sampling_rate": 16000,
        "processor_class": "WhisperProcessor",
    }
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def build_transformers_dir(model, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    import torch
    state = remap(model.state_dict())
    print(f"  权重键数: {len(state)}", flush=True)
    torch.save(state, os.path.join(out_dir, "pytorch_model.bin"))

    dims = model.dims
    n_mels = getattr(dims, "n_mels", 80)
    config = {
        "architectures": ["WhisperForConditionalGeneration"],
        "bos_token_id": 50257,
        "d_model": dims.n_audio_state,
        "decoder_attention_heads": dims.n_audio_state // 64,
        "decoder_ffn_dim": dims.n_audio_state * 4,
        "decoder_layerdrop": 0.0,
        "decoder_layers": dims.n_audio_layer,
        "decoder_start_token_id": 50258,
        "dropout": 0.0,
        "encoder_attention_heads": dims.n_audio_state // 64,
        "encoder_ffn_dim": dims.n_audio_state * 4,
        "encoder_layerdrop": 0.0,
        "encoder_layers": dims.n_audio_layer,
        "eos_token_id": 50257,
        "is_encoder_decoder": True,
        "max_length": 448,
        "max_source_positions": 1500,
        "max_target_positions": 448,
        "model_type": "whisper",
        "num_hidden_layers": dims.n_audio_layer,
        "num_mel_bins": n_mels,
        "pad_token_id": 50257,
        "scale_embedding": False,
        "use_cache": True,
        "vocab_size": 51865,
    }
    with open(os.path.join(out_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    make_tokenizer_json(os.path.join(out_dir, "tokenizer.json"))
    make_preprocessor_json(os.path.join(out_dir, "preprocessor_config.json"))
    print("  transformers 目录构建完成", flush=True)


def make_tokenizer_json(save_path):
    """whisper 全系列共用同一 multilingual BPE 词表，优先复用本机已有 base 模型的 tokenizer.json"""
    cands = [
        os.path.expanduser(
            "~/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/*/tokenizer.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "models", "faster-whisper-base", "tokenizer.json"),
    ]
    import glob
    for pattern in cands:
        for path in glob.glob(pattern):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as r, open(save_path, "w", encoding="utf-8") as w:
                    w.write(r.read())
                print(f"  tokenizer.json 复用: {path}", flush=True)
                return save_path
    # 兜底：手工构造（格式与 base 一致）
    path = find_tiktoken_file()
    merges = [l for l in open(path, encoding="utf-8") if l.strip() and not l.startswith("#")]
    merges = [l.strip() for l in merges]
    tokenizer = {
        "version": "1.0",
        "model": {"type": "BPE", "vocab": {}, "merges": merges},
        "added_tokens": [],
        "normalizer": {"type": "Precompiled"},
        "pre_tokenizer": {"type": "ByteLevel", "add_prefix_space": False, "trim_offsets": True, "use_regex": True},
        "post_processor": {"type": "ByteLevel", "add_prefix_space": False},
        "decoder": {"type": "ByteLevel", "add_prefix_space": False},
    }
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(tokenizer, f, ensure_ascii=False)
    return save_path


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pt, out = sys.argv[1], sys.argv[2]
    hf_dir = out + "_hf"

    print("1/3 加载 .pt…", flush=True)
    import whisper
    model = whisper.load_model(pt)

    print("2/3 构建 transformers 目录…", flush=True)
    build_transformers_dir(model, hf_dir)

    print("3/3 CT2 转换 (int8)…", flush=True)
    from ctranslate2.converters.transformers import TransformersConverter
    converter = TransformersConverter(hf_dir,
                                      copy_files=["tokenizer.json", "preprocessor_config.json"])
    converter.convert(out, quantization="int8", force=True)
    print(f"✅ 完成: {out}", flush=True)


if __name__ == "__main__":
    main()
