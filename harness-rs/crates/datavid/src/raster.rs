//! Single-channel float rasters: Gaussian blur (OpenCV-compatible kernel size and BORDER_REFLECT_101), area downscale,
//! bilinear resize, colour lookup tables and PNG output (files or in-memory, e.g. for `data:` URIs in SVG frames).
use anyhow::Result;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Img {
    pub w: usize,
    pub h: usize,
    pub px: Vec<f32>,
}

impl Img {
    pub fn new(w: usize, h: usize) -> Self {
        Self { w, h, px: vec![0.0; w * h] }
    }
    pub fn from(w: usize, h: usize, px: Vec<f32>) -> Self {
        assert_eq!(px.len(), w * h);
        Self { w, h, px }
    }
    #[inline]
    pub fn at(&self, x: usize, y: usize) -> f32 {
        self.px[y * self.w + x]
    }
    pub fn max(&self) -> f32 {
        self.px.iter().cloned().fold(0.0, f32::max)
    }
    pub fn map(&self, f: impl Fn(f32) -> f32) -> Img {
        Img { w: self.w, h: self.h, px: self.px.iter().map(|v| f(*v)).collect() }
    }
    /// bounding box of pixels above `thr` as (x0, y0, x1, y1) exclusive, or None
    pub fn nonzero_bbox(&self, thr: f32) -> Option<(usize, usize, usize, usize)> {
        let (mut x0, mut y0, mut x1, mut y1) = (usize::MAX, usize::MAX, 0, 0);
        for y in 0..self.h {
            for x in 0..self.w {
                if self.px[y * self.w + x] > thr {
                    x0 = x0.min(x);
                    y0 = y0.min(y);
                    x1 = x1.max(x + 1);
                    y1 = y1.max(y + 1);
                }
            }
        }
        (x0 != usize::MAX).then_some((x0, y0, x1, y1))
    }
    pub fn crop(&self, x0: usize, y0: usize, x1: usize, y1: usize) -> Img {
        let mut o = Img::new(x1 - x0, y1 - y0);
        for y in y0..y1 {
            o.px[(y - y0) * o.w..(y - y0 + 1) * o.w].copy_from_slice(&self.px[y * self.w + x0..y * self.w + x1]);
        }
        o
    }
}

fn kernel(sigma: f64) -> Vec<f32> {
    // OpenCV: ksize = cvRound(sigma * 4 * 2 + 1) | 1 for float images
    let ks = (((sigma * 8.0 + 1.0).round() as usize) | 1).max(3);
    let r = ks / 2;
    let mut k: Vec<f64> = (0..ks).map(|i| (-((i as f64 - r as f64).powi(2)) / (2.0 * sigma * sigma)).exp()).collect();
    let s: f64 = k.iter().sum();
    k.iter_mut().for_each(|v| *v /= s);
    k.into_iter().map(|v| v as f32).collect()
}

#[inline]
fn reflect101(i: isize, n: isize) -> usize {
    if n == 1 {
        return 0;
    }
    let mut i = i;
    while i < 0 || i >= n {
        if i < 0 {
            i = -i;
        }
        if i >= n {
            i = 2 * n - 2 - i;
        }
    }
    i as usize
}

/// separable Gaussian blur
pub fn blur(img: &Img, sigma: f64) -> Img {
    if sigma <= 0.0 {
        return img.clone();
    }
    let k = kernel(sigma);
    let r = (k.len() / 2) as isize;
    let (w, h) = (img.w as isize, img.h as isize);
    let mut tmp = vec![0f32; img.px.len()];
    for y in 0..img.h {
        let row = &img.px[y * img.w..(y + 1) * img.w];
        for x in 0..w {
            let mut s = 0f32;
            for (j, kv) in k.iter().enumerate() {
                s += kv * row[reflect101(x + j as isize - r, w)];
            }
            tmp[y * img.w + x as usize] = s;
        }
    }
    let mut out = vec![0f32; img.px.len()];
    for y in 0..h {
        for (j, kv) in k.iter().enumerate() {
            let sy = reflect101(y + j as isize - r, h);
            let src = &tmp[sy * img.w..(sy + 1) * img.w];
            let dst = &mut out[y as usize * img.w..(y as usize + 1) * img.w];
            for x in 0..img.w {
                dst[x] += kv * src[x];
            }
        }
    }
    Img { w: img.w, h: img.h, px: out }
}

/// downscale by an integer factor, averaging blocks (cv2.INTER_AREA for integer factors)
pub fn shrink(img: &Img, f: usize) -> Img {
    let (w, h) = (img.w / f, img.h / f);
    let mut o = Img::new(w, h);
    let n = (f * f) as f32;
    for y in 0..h {
        for x in 0..w {
            let mut s = 0.0;
            for yy in 0..f {
                for xx in 0..f {
                    s += img.px[(y * f + yy) * img.w + x * f + xx];
                }
            }
            o.px[y * w + x] = s / n;
        }
    }
    o
}

/// bilinear resize to (w, h) (pixel-centre aligned, like cv2.INTER_LINEAR)
pub fn resize(img: &Img, w: usize, h: usize) -> Img {
    let mut o = Img::new(w, h);
    let sx = img.w as f64 / w as f64;
    let sy = img.h as f64 / h as f64;
    for y in 0..h {
        let fy = ((y as f64 + 0.5) * sy - 0.5).max(0.0);
        let y0 = (fy.floor() as usize).min(img.h - 1);
        let y1 = (y0 + 1).min(img.h - 1);
        let ty = (fy - y0 as f64) as f32;
        for x in 0..w {
            let fx = ((x as f64 + 0.5) * sx - 0.5).max(0.0);
            let x0 = (fx.floor() as usize).min(img.w - 1);
            let x1 = (x0 + 1).min(img.w - 1);
            let tx = (fx - x0 as f64) as f32;
            let a = img.at(x0, y0) * (1.0 - tx) + img.at(x1, y0) * tx;
            let b = img.at(x0, y1) * (1.0 - tx) + img.at(x1, y1) * tx;
            o.px[y * w + x] = a * (1.0 - ty) + b * ty;
        }
    }
    o
}

/// a 256-entry colour ramp from (position, rgb) stops
pub fn lut(stops: &[(f64, [f64; 3])]) -> Vec<[f32; 3]> {
    (0..256)
        .map(|i| {
            let x = i as f64 / 255.0;
            let mut c = [0f32; 3];
            for ch in 0..3 {
                let xs: Vec<f64> = stops.iter().map(|s| s.0).collect();
                let ys: Vec<f64> = stops.iter().map(|s| s.1[ch]).collect();
                c[ch] = crate::ease::interp(x, &xs, &ys) as f32;
            }
            c
        })
        .collect()
}

/// RGBA8 buffer from an RGB float image (0..255) where alpha = brightness and colour is un-premultiplied: drawn with
/// `mix-blend-mode: screen`/normal over black it reproduces additive light.
pub fn light_rgba(rgb: &[[f32; 3]]) -> Vec<u8> {
    let mut out = Vec::with_capacity(rgb.len() * 4);
    for c in rgb {
        let r = c[0].clamp(0.0, 255.0);
        let g = c[1].clamp(0.0, 255.0);
        let b = c[2].clamp(0.0, 255.0);
        let a = r.max(g).max(b);
        if a <= 0.0 {
            out.extend_from_slice(&[0, 0, 0, 0]);
        } else {
            let k = 255.0 / a;
            out.extend_from_slice(&[(r * k).min(255.0) as u8, (g * k).min(255.0) as u8, (b * k).min(255.0) as u8, a as u8]);
        }
    }
    out
}

pub fn png_bytes(w: usize, h: usize, rgba: &[u8], fast: bool) -> Result<Vec<u8>> {
    let mut buf = Vec::new();
    {
        let mut e = png::Encoder::new(&mut buf, w as u32, h as u32);
        e.set_color(png::ColorType::Rgba);
        e.set_depth(png::BitDepth::Eight);
        e.set_compression(if fast { png::Compression::Fast } else { png::Compression::Default });
        let mut wr = e.write_header()?;
        wr.write_image_data(rgba)?;
    }
    Ok(buf)
}

pub fn write_png(path: &Path, w: usize, h: usize, rgba: &[u8]) -> Result<()> {
    if let Some(p) = path.parent() {
        std::fs::create_dir_all(p)?;
    }
    std::fs::write(path, png_bytes(w, h, rgba, false)?)?;
    Ok(())
}

pub fn write_png_gray(path: &Path, w: usize, h: usize, g: &[u8]) -> Result<()> {
    let f = std::fs::File::create(path)?;
    let mut e = png::Encoder::new(std::io::BufWriter::new(f), w as u32, h as u32);
    e.set_color(png::ColorType::Grayscale);
    e.set_depth(png::BitDepth::Eight);
    e.write_header()?.write_image_data(g)?;
    Ok(())
}

/// `data:image/png;base64,...` for an RGBA buffer (fast compression: used per frame)
pub fn data_uri(w: usize, h: usize, rgba: &[u8]) -> Result<String> {
    use base64::Engine;
    Ok(format!("data:image/png;base64,{}", base64::engine::general_purpose::STANDARD.encode(png_bytes(w, h, rgba, true)?)))
}
