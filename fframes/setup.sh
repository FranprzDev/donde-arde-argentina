#!/bin/bash
# One-time (per sandbox reset) setup for the fframes port. The sandbox root filesystem is wiped between sessions, so the Rust
# toolchain lives inside this folder (.toolchain/, persistent) and only the system packages are reinstalled.
# Usage: source ./setup.sh
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export RUSTUP_HOME="$HERE/.toolchain/rustup" CARGO_HOME="$HERE/.toolchain/cargo"
export CARGO_TARGET_DIR="$HERE/target" PATH="$HERE/.toolchain/cargo/bin:$PATH"
if ! command -v clang >/dev/null 2>&1; then
  sudo apt-get update -qq >/dev/null 2>&1
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential clang libclang-dev nasm yasm pkg-config \
    libx264-dev libfontconfig-dev >/dev/null 2>&1
fi
if ! command -v cargo >/dev/null 2>&1; then
  curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --no-modify-path >/dev/null 2>&1
  rustup default stable >/dev/null 2>&1
fi
cargo --version
