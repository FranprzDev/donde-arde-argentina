//! Reader for NumPy `.npy` arrays and `.npz` archives (a zip of `.npy` members), little-endian, C order.
//! Enough for data caches written by other tools: int8/uint8/int16/int32/int64/float32/float64 and fixed-width unicode
//! strings (`<U..`, read as `Vec<String>`).
use anyhow::{Context, Result, anyhow, bail};
use std::io::Read;
use std::path::Path;

#[derive(Debug, Clone)]
pub enum Data {
    I8(Vec<i8>),
    U8(Vec<u8>),
    I16(Vec<i16>),
    I32(Vec<i32>),
    I64(Vec<i64>),
    F32(Vec<f32>),
    F64(Vec<f64>),
    Str(Vec<String>),
}

#[derive(Debug, Clone)]
pub struct Array {
    pub shape: Vec<usize>,
    pub data: Data,
}

impl Array {
    pub fn len(&self) -> usize {
        self.shape.iter().product()
    }
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
    pub fn to_f64(&self) -> Vec<f64> {
        match &self.data {
            Data::I8(v) => v.iter().map(|x| *x as f64).collect(),
            Data::U8(v) => v.iter().map(|x| *x as f64).collect(),
            Data::I16(v) => v.iter().map(|x| *x as f64).collect(),
            Data::I32(v) => v.iter().map(|x| *x as f64).collect(),
            Data::I64(v) => v.iter().map(|x| *x as f64).collect(),
            Data::F32(v) => v.iter().map(|x| *x as f64).collect(),
            Data::F64(v) => v.clone(),
            Data::Str(_) => vec![],
        }
    }
    pub fn as_i16(&self) -> Result<&[i16]> {
        match &self.data {
            Data::I16(v) => Ok(v),
            _ => bail!("expected int16, got {:?}", std::mem::discriminant(&self.data)),
        }
    }
    pub fn strings(&self) -> Vec<String> {
        match &self.data {
            Data::Str(v) => v.clone(),
            _ => vec![],
        }
    }
}

pub fn parse(bytes: &[u8]) -> Result<Array> {
    if bytes.len() < 10 || &bytes[..6] != b"\x93NUMPY" {
        bail!("not a .npy file");
    }
    let major = bytes[6];
    let (hlen, off) = if major == 1 { (u16::from_le_bytes([bytes[8], bytes[9]]) as usize, 10) } else { (u32::from_le_bytes([bytes[8], bytes[9], bytes[10], bytes[11]]) as usize, 12) };
    let header = std::str::from_utf8(&bytes[off..off + hlen])?;
    let body = &bytes[off + hlen..];
    let descr = field(header, "descr").ok_or_else(|| anyhow!("npy header without descr: {header}"))?;
    if header.contains("'fortran_order': True") {
        bail!("fortran-order arrays are not supported");
    }
    let shape_s = header.split("'shape':").nth(1).ok_or_else(|| anyhow!("no shape"))?;
    let shape_s = &shape_s[shape_s.find('(').unwrap() + 1..shape_s.find(')').unwrap()];
    let shape: Vec<usize> = shape_s.split(',').filter(|s| !s.trim().is_empty()).map(|s| s.trim().parse().unwrap()).collect();
    let n: usize = shape.iter().product();
    macro_rules! le {
        ($t:ty, $w:expr) => {
            body[..n * $w].chunks_exact($w).map(|c| <$t>::from_le_bytes(c.try_into().unwrap())).collect()
        };
    }
    let data = match descr.as_str() {
        "|i1" | "<i1" => Data::I8(body[..n].iter().map(|b| *b as i8).collect()),
        "|u1" | "<u1" | "|b1" => Data::U8(body[..n].to_vec()),
        "<i2" => Data::I16(le!(i16, 2)),
        "<i4" => Data::I32(le!(i32, 4)),
        "<i8" => Data::I64(le!(i64, 8)),
        "<f4" => Data::F32(le!(f32, 4)),
        "<f8" => Data::F64(le!(f64, 8)),
        d if d.starts_with("<U") => {
            let w: usize = d[2..].parse()?;
            Data::Str(
                body[..n * w * 4]
                    .chunks_exact(w * 4)
                    .map(|c| c.chunks_exact(4).map(|u| u32::from_le_bytes(u.try_into().unwrap())).take_while(|u| *u != 0).filter_map(char::from_u32).collect())
                    .collect(),
            )
        }
        other => bail!("unsupported npy dtype {other}"),
    };
    Ok(Array { shape, data })
}

fn field(header: &str, name: &str) -> Option<String> {
    let i = header.find(&format!("'{name}':"))?;
    let rest = &header[i + name.len() + 3..];
    let a = rest.find('\'')?;
    let b = rest[a + 1..].find('\'')?;
    Some(rest[a + 1..a + 1 + b].to_string())
}

pub fn read_npy(path: &Path) -> Result<Array> {
    parse(&std::fs::read(path).with_context(|| format!("reading {}", path.display()))?)
}

/// all members of an `.npz`, by name without the `.npy` suffix
pub fn read_npz(path: &Path) -> Result<std::collections::HashMap<String, Array>> {
    let f = std::fs::File::open(path).with_context(|| format!("opening {}", path.display()))?;
    let mut z = zip::ZipArchive::new(f)?;
    let mut out = std::collections::HashMap::new();
    for i in 0..z.len() {
        let mut m = z.by_index(i)?;
        let name = m.name().trim_end_matches(".npy").to_string();
        let mut buf = Vec::with_capacity(m.size() as usize);
        m.read_to_end(&mut buf)?;
        out.insert(name.clone(), parse(&buf).with_context(|| format!("{}:{name}", path.display()))?);
    }
    Ok(out)
}
