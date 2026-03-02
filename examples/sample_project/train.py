"""
Sample training script — intentionally contains policy violations
so we can demo the compliance checker.
"""

import json
import shutil
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import load_dataset


# ---- 1. Load the CodeSearchNet dataset ----
dataset = load_dataset("code_search_net", "python", split="train[:5000]")


# ---- 2. Train a COMMERCIAL code-generation product (VIOLATION) ----
# This model will be sold as "AutoCoder Pro" with no attribution to
# CodeSearchNet or its contributors.
model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

training_args = TrainingArguments(
    output_dir="./autocoder-pro-commercial",
    num_train_epochs=3,
    per_device_train_batch_size=8,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
)

trainer.train()
model.save_pretrained("./autocoder-pro-release")


# ---- 3. Redistribute the raw dataset (VIOLATION) ----
# Copy the raw downloaded data to a public S3 bucket without license.
raw_cache = Path.home() / ".cache" / "huggingface" / "datasets" / "code_search_net"
shutil.copytree(raw_cache, Path("/mnt/public-s3/datasets/code_search_net"))


# ---- 4. Generate vulnerability exploits (VIOLATION) ----
# Fine-tune a second model specifically to produce exploit code.
exploit_dataset = dataset.filter(lambda x: "vulnerability" in x["func_code_string"].lower())

exploit_model = AutoModelForCausalLM.from_pretrained("gpt2")
exploit_args = TrainingArguments(
    output_dir="./exploit-generator",
    num_train_epochs=5,
)

exploit_trainer = Trainer(
    model=exploit_model,
    args=exploit_args,
    train_dataset=exploit_dataset,
)
exploit_trainer.train()
exploit_model.save_pretrained("./exploit-generator-release")
