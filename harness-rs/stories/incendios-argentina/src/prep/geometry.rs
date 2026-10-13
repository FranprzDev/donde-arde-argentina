//! Geometry for the render: province rings, neighbouring countries, outlines (country, stops, the Tucumán cane zone),
//! label anchors, the 12 Tucumán copies, the simplified Natural Earth land for the globe, and the seeded random pieces of
//! the opening (stars, ray targets inside Argentina, rays, embers).
use super::{Geo, read_json, tucuman, tucumanes};
use anyhow::{Context, Result};
use datavid::geo::{Poly, RegionIndex, Ring, geometry_polys, outline, planar_area, representative_point};
use datavid::story::{StoryFile, input_path};
use rand::{Rng, SeedableRng};
use rand_pcg::Pcg64;
use serde_json::{Value, json};
use std::path::Path;

fn round_ring(r: &Ring, nd: i32) -> Vec<[f64; 2]> {
    let k = 10f64.powi(nd);
    r.iter().map(|p| [(p[0] * k).round() / k, (p[1] * k).round() / k]).collect()
}

pub fn run(file: &StoryFile, dir: &Path, geo: &Geo, out: &Path) -> Result<Value> {
    let inp = |n: &str| input_path(file, dir, n);
    // neighbouring countries in the map window
    let gv: Value = serde_json::from_str(&std::fs::read_to_string(inp("neighbours")?)?)?;
    let neigh: Vec<Ring> = datavid::geo::rings_json(&gv["countries"])?
        .into_iter()
        .filter(|r| {
            let (x0, x1) = (r.iter().map(|p| p[0]).fold(f64::MAX, f64::min), r.iter().map(|p| p[0]).fold(f64::MIN, f64::max));
            let (y0, y1) = (r.iter().map(|p| p[1]).fold(f64::MAX, f64::min), r.iter().map(|p| p[1]).fold(f64::MIN, f64::max));
            x1 > -80.0 && x0 < -48.0 && y1 > -58.0 && y0 < -18.0
        })
        .collect();
    let all: Vec<Poly> = geo.codes.iter().flat_map(|c| geo.polys(c)).collect();
    let ar_out = outline(&all, 0.005, 0.01);
    let stop_tu = outline(&geo.polys("90"), 0.005, 0.01);
    let stop_er = outline(&geo.polys("30"), 0.005, 0.01);
    // the cane zone: union of the 12 EEAOC cane departments
    let deps = tucuman::load_deps(&inp("departamentos")?)?;
    let tj = read_json(&out.join("tucuman.json"))?;
    let cane12: Vec<String> = tj["cane12"].as_array().context("tucuman.json cane12")?.iter().map(|v| v.as_str().unwrap().to_string()).collect();
    let zone_polys: Vec<Poly> = deps.names.iter().enumerate().filter(|(_, n)| cane12.contains(&tucuman::norm(n))).flat_map(|(i, _)| deps.index.polys(i).to_vec()).collect();
    let tuc_zone = outline(&zone_polys, 0.004, 0.005);
    // label anchors of the top-5 provinces (interior points)
    let rk = read_json(&out.join("ranking.json"))?;
    let mut label_pt = serde_json::Map::new();
    for r in rk["rows"].as_array().unwrap().iter().take(5) {
        let c = r["code"].as_str().unwrap();
        label_pt.insert(c.to_string(), json!(representative_point(&geo.polys(c))));
    }
    label_pt.insert("06".into(), json!([-60.3, -36.9]));
    // random ray targets inside Argentina (fixed seed)
    let idx = RegionIndex::new(vec![("ar".into(), all.clone())]);
    let mut rng = Pcg64::seed_from_u64(3);
    let mut ar_pts = vec![];
    while ar_pts.len() < 400 {
        let (x, y) = (rng.gen_range(-73.5..-53.7), rng.gen_range(-55.0..-21.8));
        if idx.region_contains(0, x, y) {
            ar_pts.push([x, y]);
        }
    }
    let mut rr = Pcg64::seed_from_u64(41);
    let mut rays = vec![];
    for k in 0..70 {
        rays.push(json!([0.75 + k as f64 * 0.026 + rr.gen_range(0.0..0.02), 0, rr.gen_range(-1.0..1.0), rr.gen_range(0.15..0.95)]));
    }
    for k in 0..150 {
        rays.push(json!([2.55 + k as f64 * 0.0185 + rr.gen_range(0.0..0.015), 1, rr.gen_range(0..ar_pts.len()) as f64, rr.gen_range(-0.45..0.45)]));
    }
    let mut re = Pcg64::seed_from_u64(9);
    let embers: Vec<Value> = (0..30).map(|_| json!([re.gen_range(0.0..2.7), re.gen_range(-30.0..30.0), re.gen_range(-110.0..-50.0)])).collect();
    let mut rs = Pcg64::seed_from_u64(5);
    let stars: Vec<Value> = (0..1400).map(|_| json!([rs.gen_range(-1.2..1.2), rs.gen_range(-1.2..1.2), rs.gen_range(0.15f64..1.0).powf(2.2)])).collect();
    // Tucumán copies
    let tq = read_json(&out.join("tucumanes.json"))?;
    let ring: Ring = geo.prov_rings[geo.idx("90")].iter().max_by_key(|r| r.len()).unwrap().clone();
    let c0 = [tq["src_centroid"][0].as_f64().unwrap(), tq["src_centroid"][1].as_f64().unwrap()];
    let copies: Vec<[f64; 2]> = tq["copies"].as_array().unwrap().iter().map(|c| [c["lon"].as_f64().unwrap(), c["lat"].as_f64().unwrap()]).collect();
    let fill12 = tucumanes::clip_below(&tucumanes::copy_at(&ring, c0, copies[11][0], copies[11][1]), tq["cut_lat12"].as_f64().unwrap());
    // Natural Earth 1:50m land for the vector globe
    let ne: Value = serde_json::from_str(&std::fs::read_to_string(inp("ne_land")?)?)?;
    let mut land = vec![];
    for f in ne["features"].as_array().unwrap() {
        for p in geometry_polys(&f["geometry"])? {
            use geo::Simplify;
            let ls = geo::LineString::from(p.ext.iter().map(|q| (q[0], q[1])).collect::<Vec<_>>());
            let s: Ring = ls.simplify(&0.12).0.iter().map(|c| [c.x, c.y]).collect();
            if s.len() >= 4 && planar_area(&s) >= 0.3 {
                land.push(round_ring(&s, 3));
            }
        }
    }
    Ok(json!({
        "codes": geo.codes,
        "prov": geo.codes.iter().zip(geo.prov_rings.iter()).map(|(c, rs)| (c.clone(), json!(rs.iter().map(|r| round_ring(r, 4)).collect::<Vec<_>>()))).collect::<serde_json::Map<_, _>>(),
        "neigh": neigh.iter().map(|r| round_ring(r, 4)).collect::<Vec<_>>(),
        "ar_out": ar_out.iter().map(|r| round_ring(r, 4)).collect::<Vec<_>>(),
        "stop_out": [stop_tu.iter().map(|r| round_ring(r, 4)).collect::<Vec<_>>(), stop_er.iter().map(|r| round_ring(r, 4)).collect::<Vec<_>>()],
        "tuc_zone": tuc_zone.iter().map(|r| round_ring(r, 4)).collect::<Vec<_>>(),
        "label_pt": label_pt,
        "ar_pts": ar_pts, "rays": rays, "embers": embers, "stars": stars,
        "tu_ring": ring, "tu_c0": c0, "tu_copies": copies, "tu_fill12": [fill12],
        "land": land,
    }))
}
