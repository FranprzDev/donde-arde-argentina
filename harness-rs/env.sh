# Toolchain environment for this sandbox (Rust lives in a persistent folder; see README "Sandbox notes").
export RUSTUP_HOME=${RUSTUP_HOME:-/workspace/work/contar-con-datos-fuego/fframes/.toolchain/rustup}
export CARGO_HOME=${CARGO_HOME:-/workspace/work/contar-con-datos-fuego/fframes/.toolchain/cargo}
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-/workspace/work/contar-con-datos-fuego/fframes/target}
export X264_LIB_DIR=${X264_LIB_DIR:-/workspace/work/contar-con-datos-fuego/fframes/.toolchain/x264/lib}
export PATH="$CARGO_HOME/bin:$PATH"
