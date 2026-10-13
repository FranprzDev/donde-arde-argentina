//! Verifies the Rust camera port against the Python camera (data/cam_check.json = render_v10.cam_at for every frame).
use incendios_fframes::{cam::cam_at, data::V10};

fn main() {
    let here = env!("CARGO_MANIFEST_DIR");
    let d = V10::load(&format!("{here}/data/v10.json")).unwrap();
    let py: Vec<[f64; 5]> = serde_json::from_str(&std::fs::read_to_string(format!("{here}/data/cam_check.json")).unwrap()).unwrap();
    let mut worst = (0.0f64, 0usize);
    for (f, c) in py.iter().enumerate() {
        let r = cam_at(&d, f as f64 / 30.0);
        // compare in screen pixels: centre offset and the projected position of the camera centre
        let err = (0..5).map(|i| (r[i] - c[i]).abs() * if i < 2 { c[2] } else { 1.0 }).fold(0.0, f64::max);
        if err > worst.0 {
            worst = (err, f);
        }
    }
    println!("frames {}  worst camera error {:.6} px at frame {}", py.len(), worst.0, worst.1);
    assert!(worst.0 < 0.01, "camera port differs from Python");
}
