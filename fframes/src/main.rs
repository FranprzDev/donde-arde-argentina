//! Command line of the port (fframes::cli): render, frame, strip, inspect, timeline, ...
//! Run from this folder: `cargo run --release -- render 0s..20.79s -o build/a.mp4` (see README.md).
use fframes::{EncoderOptions, MediaDirectory, RenderOptions, cli};
use incendios_fframes::{IncendiosVideo, data::V10};
use std::process::ExitCode;

fn main() -> ExitCode {
    let here = env!("CARGO_MANIFEST_DIR");
    let d = V10::load(&format!("{here}/data/v10.json")).expect("data/v10.json (run prep/export_data.py)");
    if !d.sources.reading_ok {
        eprintln!(
            "note: closing card holds {:.2} s for {} words (reading rule needs {:.1} s, scan rate {:.1} s)",
            d.sources.hold, d.sources.words, d.sources.strict_need, d.sources.scan_need
        );
    }
    let video = IncendiosVideo::new(d);
    // fonts (media/) and georeferenced rasters (assets/) are read at runtime
    let fonts = MediaDirectory::read_folder(format!("{here}/media")).expect("media/");
    let assets = MediaDirectory::read_folder(format!("{here}/assets")).expect("assets/");
    let fonts_p = fonts.process_media_source().expect("fonts");
    let assets_p = assets.process_media_source().expect("assets");
    let media = fframes::CombinedMediaProvider::from([
        &fonts_p as &dyn fframes::MediaProvider,
        &assets_p as &dyn fframes::MediaProvider,
    ]);

    cli::new(
        &video,
        RenderOptions {
            media: Some(&media),
            video_encoder_options: EncoderOptions {
                preferred_encoder: Some("libx264"),
                // same encode as the v10 chunks (veryfast, crf 14) so render times compare like for like
                codec_params: Some(&[("crf", "14"), ("preset", "veryfast")]),
                ..Default::default()
            },
            ..Default::default()
        },
    )
    .run()
}
