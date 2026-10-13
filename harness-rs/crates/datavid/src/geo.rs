//! Geometry for data prep: polygons in lon/lat, fast point-in-polygon, distance to a boundary, rasterisation on a regular
//! lon/lat grid (pixel centres, last shape wins: the rasterio/GDAL default), geodesic areas on WGS84 (GeographicLib),
//! outline unions and simplification (the `geo` crate), representative points and GeoJSON reading.
use anyhow::{Result, anyhow};
use serde_json::Value;

pub type Ring = Vec<[f64; 2]>;

/// A polygon: exterior ring plus holes.
#[derive(Debug, Clone, Default)]
pub struct Poly {
    pub ext: Ring,
    pub holes: Vec<Ring>,
}

/// A regular lon/lat grid: west edge `lon0`, north edge `lat1`, cell size `d` (degrees), `w` x `h` cells.
#[derive(Debug, Clone, Copy)]
pub struct Grid {
    pub lon0: f64,
    pub lat1: f64,
    pub d: f64,
    pub w: usize,
    pub h: usize,
}

fn ring_bbox(r: &Ring) -> [f64; 4] {
    let mut b = [f64::MAX, f64::MAX, f64::MIN, f64::MIN];
    for p in r {
        b[0] = b[0].min(p[0]);
        b[1] = b[1].min(p[1]);
        b[2] = b[2].max(p[0]);
        b[3] = b[3].max(p[1]);
    }
    b
}

/// ring with its edges bucketed by latitude, for fast crossing-number tests
#[derive(Debug, Clone)]
struct IRing {
    bbox: [f64; 4],
    y0: f64,
    dy: f64,
    bins: Vec<Vec<(f64, f64, f64, f64)>>,
}

impl IRing {
    fn new(r: &Ring) -> Self {
        let bbox = ring_bbox(r);
        let nb = (r.len() / 8).clamp(1, 4096);
        let dy = ((bbox[3] - bbox[1]) / nb as f64).max(1e-12);
        let mut bins = vec![vec![]; nb];
        let n = r.len();
        for i in 0..n {
            let a = r[i];
            let b = r[(i + 1) % n];
            if a == b {
                continue;
            }
            let (lo, hi) = (a[1].min(b[1]), a[1].max(b[1]));
            let i0 = (((lo - bbox[1]) / dy).floor() as isize).clamp(0, nb as isize - 1) as usize;
            let i1 = (((hi - bbox[1]) / dy).floor() as isize).clamp(0, nb as isize - 1) as usize;
            for bin in bins.iter_mut().take(i1 + 1).skip(i0) {
                bin.push((a[0], a[1], b[0], b[1]));
            }
        }
        Self { bbox, y0: bbox[1], dy, bins }
    }
    fn contains(&self, x: f64, y: f64) -> bool {
        if x < self.bbox[0] || x > self.bbox[2] || y < self.bbox[1] || y > self.bbox[3] {
            return false;
        }
        let bi = (((y - self.y0) / self.dy).floor() as isize).clamp(0, self.bins.len() as isize - 1) as usize;
        let mut inside = false;
        for &(x0, y0, x1, y1) in &self.bins[bi] {
            if (y0 > y) != (y1 > y) {
                let xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0);
                if x < xi {
                    inside = !inside;
                }
            }
        }
        inside
    }
}

/// Point-in-polygon index for a set of named regions (each a list of polygons).
#[derive(Debug, Clone)]
pub struct RegionIndex {
    pub ids: Vec<String>,
    regions: Vec<Vec<(IRing, Vec<IRing>)>>,
    raw: Vec<Vec<Poly>>,
}

impl RegionIndex {
    pub fn new(regions: Vec<(String, Vec<Poly>)>) -> Self {
        let ids = regions.iter().map(|r| r.0.clone()).collect();
        let idx = regions.iter().map(|(_, ps)| ps.iter().map(|p| (IRing::new(&p.ext), p.holes.iter().map(IRing::new).collect())).collect()).collect();
        let raw = regions.into_iter().map(|r| r.1).collect();
        Self { ids, regions: idx, raw }
    }
    pub fn region_contains(&self, i: usize, x: f64, y: f64) -> bool {
        self.regions[i].iter().any(|(e, hs)| e.contains(x, y) && !hs.iter().any(|h| h.contains(x, y)))
    }
    /// first region (in index order) containing the point
    pub fn locate(&self, x: f64, y: f64) -> Option<usize> {
        (0..self.regions.len()).find(|&i| self.region_contains(i, x, y))
    }
    /// distance (degrees, planar like shapely) from a point to region i
    pub fn distance(&self, i: usize, x: f64, y: f64) -> f64 {
        let mut best = f64::MAX;
        for p in &self.raw[i] {
            for r in std::iter::once(&p.ext).chain(p.holes.iter()) {
                let n = r.len();
                for k in 0..n {
                    best = best.min(seg_dist(x, y, r[k], r[(k + 1) % n]));
                }
            }
        }
        best
    }
    /// region containing the point, else the nearest one (shapely `distance` semantics)
    pub fn locate_or_nearest(&self, x: f64, y: f64) -> (usize, bool) {
        if let Some(i) = self.locate(x, y) {
            return (i, true);
        }
        let mut best = (0, f64::MAX);
        for i in 0..self.regions.len() {
            let d = self.distance(i, x, y);
            if d < best.1 {
                best = (i, d);
            }
        }
        (best.0, false)
    }
    pub fn polys(&self, i: usize) -> &[Poly] {
        &self.raw[i]
    }
}

fn seg_dist(x: f64, y: f64, a: [f64; 2], b: [f64; 2]) -> f64 {
    let (dx, dy) = (b[0] - a[0], b[1] - a[1]);
    let l2 = dx * dx + dy * dy;
    let t = if l2 > 0.0 { (((x - a[0]) * dx + (y - a[1]) * dy) / l2).clamp(0.0, 1.0) } else { 0.0 };
    (x - a[0] - t * dx).hypot(y - a[1] - t * dy)
}

/// Burn rings into a grid (value per ring; pixel centre inside the ring, even-odd; later rings overwrite earlier ones),
/// i.e. `rasterio.features.rasterize` with all_touched=False.
pub fn rasterize(shapes: &[(&Ring, u8)], g: &Grid) -> Vec<u8> {
    let mut out = vec![0u8; g.w * g.h];
    let mut xs: Vec<f64> = Vec::new();
    for (ring, v) in shapes {
        let bb = ring_bbox(ring);
        let r0 = (((g.lat1 - bb[3]) / g.d) - 0.5).floor().max(0.0) as usize;
        let r1 = ((((g.lat1 - bb[1]) / g.d) - 0.5).ceil() as isize).clamp(0, g.h as isize - 1) as usize;
        let n = ring.len();
        for row in r0..=r1.min(g.h.saturating_sub(1)) {
            let y = g.lat1 - (row as f64 + 0.5) * g.d;
            xs.clear();
            for i in 0..n {
                let a = ring[i];
                let b = ring[(i + 1) % n];
                if (a[1] > y) != (b[1] > y) {
                    xs.push(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
                }
            }
            xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
            for pr in xs.chunks_exact(2) {
                // columns whose centre lon0 + (c + .5) d lies in [pr0, pr1)
                let c0 = ((pr[0] - g.lon0) / g.d - 0.5).ceil().max(0.0) as usize;
                let c1 = ((pr[1] - g.lon0) / g.d - 0.5).ceil() as isize - 1;
                let c1 = c1.min(g.w as isize - 1);
                if c1 < c0 as isize {
                    continue;
                }
                for c in c0..=(c1 as usize) {
                    out[row * g.w + c] = *v;
                }
            }
        }
    }
    out
}

/// geodesic area (m², WGS84) of a polygon (exterior minus holes)
pub fn geodesic_area_m2(p: &Poly) -> f64 {
    use geographiclib_rs::{Geodesic, PolygonArea, Winding};
    let g = Geodesic::wgs84();
    let ring_area = |r: &Ring| {
        let mut pa = PolygonArea::new(&g, Winding::CounterClockwise);
        let pts: &[[f64; 2]] = if r.len() > 1 && r[0] == r[r.len() - 1] { &r[..r.len() - 1] } else { r };
        for q in pts {
            pa.add_point(q[1], q[0]);
        }
        let (_, a, _) = pa.compute(false);
        // the unsigned area of a clockwise ring comes back as its complement on the ellipsoid
        const EARTH_M2: f64 = 510_065_621_724_088.5;
        let a = a.abs();
        if a > EARTH_M2 / 2.0 { EARTH_M2 - a } else { a }
    };
    ring_area(&p.ext) - p.holes.iter().map(ring_area).sum::<f64>()
}

pub fn planar_area(r: &Ring) -> f64 {
    let n = r.len();
    let mut s = 0.0;
    for i in 0..n {
        let (a, b) = (r[i], r[(i + 1) % n]);
        s += a[0] * b[1] - b[0] * a[1];
    }
    (s / 2.0).abs()
}

pub fn centroid(r: &Ring) -> [f64; 2] {
    let n = r.len();
    let (mut a, mut cx, mut cy) = (0.0, 0.0, 0.0);
    for i in 0..n {
        let (p, q) = (r[i], r[(i + 1) % n]);
        let cr = p[0] * q[1] - q[0] * p[1];
        a += cr;
        cx += (p[0] + q[0]) * cr;
        cy += (p[1] + q[1]) * cr;
    }
    [cx / (3.0 * a), cy / (3.0 * a)]
}

/// GEOS-style interior point of a polygon: the midpoint of the widest interior run of the horizontal line through the
/// middle of the bounding box (good label anchor, always inside).
pub fn representative_point(polys: &[Poly]) -> [f64; 2] {
    let p = polys.iter().max_by(|a, b| planar_area(&a.ext).partial_cmp(&planar_area(&b.ext)).unwrap()).unwrap();
    let bb = ring_bbox(&p.ext);
    let y = (bb[1] + bb[3]) / 2.0;
    let mut xs = vec![];
    for r in std::iter::once(&p.ext).chain(p.holes.iter()) {
        let n = r.len();
        for i in 0..n {
            let (a, b) = (r[i], r[(i + 1) % n]);
            if (a[1] > y) != (b[1] > y) {
                xs.push(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
            }
        }
    }
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let mut best = (0.0, [(bb[0] + bb[2]) / 2.0, y]);
    for pr in xs.chunks_exact(2) {
        if pr[1] - pr[0] > best.0 {
            best = (pr[1] - pr[0], [(pr[0] + pr[1]) / 2.0, y]);
        }
    }
    best.1
}

fn to_geo(p: &Poly) -> geo::Polygon<f64> {
    let ls = |r: &Ring| geo::LineString::from(r.iter().map(|q| (q[0], q[1])).collect::<Vec<_>>());
    geo::Polygon::new(ls(&p.ext), p.holes.iter().map(ls).collect())
}

/// Union of polygons, simplified with tolerance `tol` (Douglas-Peucker), keeping exterior rings with planar area > `min_area`.
pub fn outline(polys: &[Poly], tol: f64, min_area: f64) -> Vec<Ring> {
    use geo::{BooleanOps, Simplify};
    let mut acc: Option<geo::MultiPolygon<f64>> = None;
    // pairwise tree union keeps every step small
    let mut parts: Vec<geo::MultiPolygon<f64>> = polys.iter().filter(|p| p.ext.len() >= 4).map(|p| geo::MultiPolygon::new(vec![to_geo(p)])).collect();
    while parts.len() > 1 {
        let mut next = vec![];
        for ch in parts.chunks(2) {
            next.push(if ch.len() == 2 { ch[0].union(&ch[1]) } else { ch[0].clone() });
        }
        parts = next;
    }
    if let Some(p) = parts.pop() {
        acc = Some(p);
    }
    let Some(u) = acc else { return vec![] };
    let s = if tol > 0.0 { u.simplify(&tol) } else { u };
    s.0.iter()
        .map(|p| p.exterior().0.iter().map(|c| [c.x, c.y]).collect::<Ring>())
        .filter(|r| planar_area(r) > min_area)
        .collect()
}

/// Intersect polygons with a lon/lat box, then outline.
pub fn clip_box(polys: &[Poly], bx: [f64; 4]) -> Vec<Poly> {
    use geo::BooleanOps;
    let b = geo::Rect::new((bx[0], bx[1]), (bx[2], bx[3])).to_polygon();
    let mut out = vec![];
    for p in polys {
        for q in to_geo(p).intersection(&b).0 {
            out.push(Poly { ext: q.exterior().0.iter().map(|c| [c.x, c.y]).collect(), holes: q.interiors().iter().map(|h| h.0.iter().map(|c| [c.x, c.y]).collect()).collect() });
        }
    }
    out
}

fn ring_of(v: &Value) -> Result<Ring> {
    v.as_array().ok_or_else(|| anyhow!("bad ring"))?.iter().map(|p| Ok([p[0].as_f64().ok_or_else(|| anyhow!("bad coord"))?, p[1].as_f64().ok_or_else(|| anyhow!("bad coord"))?])).collect()
}

/// polygons of a GeoJSON geometry (Polygon or MultiPolygon)
pub fn geometry_polys(g: &Value) -> Result<Vec<Poly>> {
    let poly = |c: &Value| -> Result<Poly> {
        let rs = c.as_array().ok_or_else(|| anyhow!("bad polygon"))?;
        Ok(Poly { ext: ring_of(&rs[0])?, holes: rs[1..].iter().map(ring_of).collect::<Result<_>>()? })
    };
    match g["type"].as_str() {
        Some("Polygon") => Ok(vec![poly(&g["coordinates"])?]),
        Some("MultiPolygon") => g["coordinates"].as_array().unwrap().iter().map(poly).collect(),
        other => Err(anyhow!("unsupported geometry {other:?}")),
    }
}

/// a JSON list of rings (`[[[lon, lat], ...], ...]`) as exterior-only polygons
pub fn rings_json(v: &Value) -> Result<Vec<Ring>> {
    v.as_array().ok_or_else(|| anyhow!("expected a list of rings"))?.iter().map(ring_of).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn square() {
        let r: Ring = vec![[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]];
        let idx = RegionIndex::new(vec![("a".into(), vec![Poly { ext: r.clone(), holes: vec![] }])]);
        assert!(idx.region_contains(0, 1.0, 1.0));
        assert!(!idx.region_contains(0, 3.0, 1.0));
        let g = Grid { lon0: 0.0, lat1: 2.0, d: 0.5, w: 6, h: 4 };
        let m = rasterize(&[(&r, 1)], &g);
        assert_eq!(m.iter().filter(|v| **v == 1).count(), 16);
    }
}
