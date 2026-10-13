//! Link the prebuilt FFmpeg 9 (aarch64) shipped by ffmpeg-sys-fframes against libx264 ABI 163, the x264 it was built with.
//! Debian 13 ships x264 ABI 164/165, so `.toolchain/x264/lib` holds Ubuntu 22.04's libx264.so.163 (see setup.sh); the binary
//! finds it at run time through an rpath.
fn main() {
    let dir = format!("{}/.toolchain/x264/lib", env!("CARGO_MANIFEST_DIR"));
    if std::path::Path::new(&dir).join("libx264.so.163").exists() {
        println!("cargo:rustc-link-search=native={dir}");
        println!("cargo:rustc-link-arg=-Wl,-rpath,{dir}");
    }
    println!("cargo:rerun-if-changed=build.rs");
}
