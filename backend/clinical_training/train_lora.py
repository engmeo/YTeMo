"""Optional LoRA/QLoRA SFT runner.

Install backend/requirements-training.txt on a dedicated training machine with a
compatible GPU. This script never runs during API startup and never downloads
weights into the Git repository.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Hugging Face model ID or local path")
    parser.add_argument("--dataset", required=True, help="Governed JSONL from prepare_dataset.py")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--qlora", action="store_true")
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    args = parser.parse_args()

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer, Trainer,
            TrainingArguments, DataCollatorForLanguageModeling, BitsAndBytesConfig,
        )
    except ImportError as exc:
        raise SystemExit("Thiếu training dependencies. Cài backend/requirements-training.txt trên máy training.") from exc

    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        raise SystemExit(f"Không tìm thấy dataset: {dataset_path}")
    raw = load_dataset("json", data_files=str(dataset_path), split="train")
    if len(raw) == 0:
        raise SystemExit("Dataset rỗng.")
    required = {"instruction", "response", "evidence_state", "source_provenance", "training_record_sha256"}
    missing = required - set(raw.column_names)
    if missing:
        raise SystemExit(f"Dataset thiếu provenance fields: {sorted(missing)}")

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization = None
    if args.qlora:
        if not torch.cuda.is_available():
            raise SystemExit("QLoRA cần CUDA GPU; không tự động chuyển sang CPU.")
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        device_map="auto",
        quantization_config=quantization,
        torch_dtype="auto",
    )
    if args.qlora:
        model = prepare_model_for_kbit_training(model)

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM",
        target_modules="all-linear",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    def format_record(row):
        evidence = (
            f"Trạng thái bằng chứng: {row['evidence_state']}\n"
            f"Tóm tắt bằng chứng: {row.get('evidence_summary', '')}\n"
        )
        user_input = f"{row['instruction']}\n{row.get('input', '')}\n{evidence}".strip()
        messages = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": row["response"]},
        ]
        if getattr(tokenizer, "chat_template", None):
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        else:
            text = f"User:\n{user_input}\nAssistant:\n{row['response']}{tokenizer.eos_token}"
        return {"text": text}

    formatted = raw.map(format_record)
    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=args.max_length)
    tokenized = formatted.map(tokenize, batched=True, remove_columns=formatted.column_names)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="epoch",
        report_to=[],
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        optim="paged_adamw_8bit" if args.qlora else "adamw_torch",
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    model.save_pretrained(output / "adapter")
    tokenizer.save_pretrained(output / "adapter")
    manifest = {
        "base_model": args.model,
        "dataset": str(dataset_path),
        "dataset_rows": len(raw),
        "method": "QLoRA" if args.qlora else "LoRA",
        "max_length": args.max_length,
        "epochs": args.epochs,
        "clinical_release_status": "NOT_VALIDATED",
        "note": "Training completion does not authorize patient-facing clinical use.",
    }
    (output / "training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
