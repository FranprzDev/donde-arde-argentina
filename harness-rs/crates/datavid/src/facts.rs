//! Facts: every number shown on screen, computed by the story's data code and saved as `build/facts.json`.
//!
//! Templates use `{name}` or `{name|filter|filter:arg}`. Filters (Spanish number formatting by default):
//! `int` (thousands with "."), `dec:N` (N decimals with ","), `div:X`, `mul:X`, `round`, `floor`, `ceil`,
//! `pct` (×100, rounded), `upper`, `lower`, `ddmmyyyy` (from "YYYY-MM-DD"), `mon_es` (from "YYYY-MM-DD": "DIC 2024").
use crate::story::AssertCfg;
use anyhow::{Context, Result, anyhow, bail};
use indexmap::IndexMap;
use serde_json::Value;
use std::path::Path;

#[derive(Debug, Clone, Default)]
pub struct Facts {
    pub map: IndexMap<String, Value>,
    /// where each fact came from (file / computation), saved next to the values
    pub src: IndexMap<String, String>,
}

pub fn es_int(n: f64) -> String {
    let neg = n < 0.0;
    let s = format!("{}", n.abs().trunc() as i64);
    let mut out = String::new();
    for (i, ch) in s.chars().enumerate() {
        if i > 0 && (s.len() - i) % 3 == 0 {
            out.push('.');
        }
        out.push(ch);
    }
    if neg { format!("-{out}") } else { out }
}
pub fn es_dec(x: f64, d: usize) -> String {
    format!("{x:.d$}").replace('.', ",")
}

const MON_ES: [&str; 12] = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"];

impl Facts {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn set(&mut self, name: &str, v: impl Into<Value>, src: &str) {
        self.map.insert(name.to_string(), v.into());
        self.src.insert(name.to_string(), src.to_string());
    }
    pub fn get(&self, name: &str) -> Result<&Value> {
        self.map.get(name).ok_or_else(|| anyhow!("unknown fact '{name}'"))
    }
    pub fn num(&self, name: &str) -> f64 {
        self.map.get(name).and_then(|v| v.as_f64()).unwrap_or_else(|| panic!("fact '{name}' is missing or not a number"))
    }
    pub fn str(&self, name: &str) -> String {
        match self.map.get(name) {
            Some(Value::String(s)) => s.clone(),
            Some(v) => v.to_string(),
            None => panic!("fact '{name}' is missing"),
        }
    }
    pub fn numbers(&self) -> Vec<(String, f64)> {
        self.map.iter().filter_map(|(k, v)| v.as_f64().map(|f| (k.clone(), f))).collect()
    }
    pub fn save(&self, path: &Path) -> Result<()> {
        let mut o = serde_json::Map::new();
        for (k, v) in &self.map {
            o.insert(k.clone(), serde_json::json!({"value": v, "source": self.src.get(k).cloned().unwrap_or_default()}));
        }
        if let Some(p) = path.parent() {
            std::fs::create_dir_all(p)?;
        }
        std::fs::write(path, serde_json::to_string_pretty(&Value::Object(o))?)?;
        Ok(())
    }
    pub fn load(path: &Path) -> Result<Self> {
        let v: Value = serde_json::from_str(&std::fs::read_to_string(path).with_context(|| format!("{} (run `prep` and `facts` first)", path.display()))?)?;
        let mut f = Self::new();
        for (k, e) in v.as_object().ok_or_else(|| anyhow!("facts.json is not an object"))? {
            f.map.insert(k.clone(), e["value"].clone());
            f.src.insert(k.clone(), e["source"].as_str().unwrap_or("").to_string());
        }
        Ok(f)
    }

    /// the template without its placeholders (used to find digits typed by hand)
    pub fn literal_part(tpl: &str) -> String {
        let mut out = String::new();
        let mut depth = 0;
        for ch in tpl.chars() {
            match ch {
                '{' => depth += 1,
                '}' => depth -= 1,
                _ if depth == 0 => out.push(ch),
                _ => {}
            }
        }
        out
    }

    pub fn render(&self, tpl: &str) -> Result<String> {
        let mut out = String::new();
        let mut rest = tpl;
        while let Some(i) = rest.find('{') {
            out.push_str(&rest[..i]);
            let j = rest[i..].find('}').ok_or_else(|| anyhow!("unclosed '{{' in «{tpl}»"))?;
            out.push_str(&self.placeholder(&rest[i + 1..i + j]).with_context(|| format!("in «{tpl}»"))?);
            rest = &rest[i + j + 1..];
        }
        out.push_str(rest);
        Ok(out)
    }

    fn placeholder(&self, ph: &str) -> Result<String> {
        let mut parts = ph.split('|');
        let name = parts.next().unwrap().trim();
        let mut v = self.get(name)?.clone();
        let mut fmt: Option<String> = None;
        for f in parts {
            let (f, arg) = f.split_once(':').map(|(a, b)| (a.trim(), Some(b.trim()))).unwrap_or((f.trim(), None));
            let x = || v.as_f64().ok_or_else(|| anyhow!("filter '{f}' needs a number, fact '{name}' is {v}"));
            let a = || -> Result<f64> { arg.ok_or_else(|| anyhow!("filter '{f}' needs an argument"))?.parse::<f64>().map_err(|e| anyhow!("{e}")) };
            match f {
                "div" => v = Value::from(x()? / a()?),
                "mul" => v = Value::from(x()? * a()?),
                "round" => v = Value::from(x()?.round()),
                "floor" => v = Value::from(x()?.floor()),
                "ceil" => v = Value::from(x()?.ceil()),
                "pct" => v = Value::from((x()? * 100.0).round()),
                "int" => fmt = Some(es_int(x()?)),
                "dec" => fmt = Some(es_dec(x()?, a()? as usize)),
                "upper" => fmt = Some(fmt.take().unwrap_or_else(|| as_text(&v)).to_uppercase()),
                "lower" => fmt = Some(fmt.take().unwrap_or_else(|| as_text(&v)).to_lowercase()),
                "ddmmyyyy" => {
                    let s = as_text(&v);
                    let p: Vec<&str> = s[..10].split('-').collect();
                    fmt = Some(format!("{}/{}/{}", p[2], p[1], p[0]));
                }
                "mon_es" => {
                    let s = as_text(&v);
                    let m: usize = s[5..7].parse()?;
                    fmt = Some(format!("{} {}", MON_ES[m - 1], &s[..4]));
                }
                "year" => fmt = Some(as_text(&v)[..4].to_string()),
                _ => bail!("unknown filter '{f}'"),
            }
        }
        Ok(fmt.unwrap_or_else(|| as_text(&v)))
    }

    /// Check the asserts declared in story.toml. Returns one line per assert (for the QA report); fails on the first broken.
    pub fn check(&self, asserts: &[AssertCfg]) -> Result<Vec<String>> {
        let mut lines = vec![];
        let mut bad = vec![];
        for a in asserts {
            let v = self.get(&a.fact)?;
            let mut ok = true;
            let mut desc = vec![];
            if let Some(e) = &a.eq {
                let ej: Value = serde_json::to_value(e)?;
                let same = match (v.as_f64(), ej.as_f64()) {
                    (Some(x), Some(y)) => (x - y).abs() < 1e-9,
                    _ => *v == ej,
                };
                ok &= same;
                desc.push(format!("== {ej}"));
            }
            let x = v.as_f64();
            for (op, lim) in [(">", a.gt), (">=", a.ge), ("<", a.lt), ("<=", a.le)] {
                if let Some(l) = lim {
                    let xv = x.ok_or_else(|| anyhow!("assert on '{}' needs a number", a.fact))?;
                    ok &= match op {
                        ">" => xv > l,
                        ">=" => xv >= l,
                        "<" => xv < l,
                        _ => xv <= l,
                    };
                    desc.push(format!("{op} {l}"));
                }
            }
            let line = format!("{} {} {} (value {}) {}", if ok { "ok  " } else { "FAIL" }, a.fact, desc.join(" and "), v, a.why);
            if !ok {
                bad.push(line.clone());
            }
            lines.push(line);
        }
        if !bad.is_empty() {
            bail!("fact asserts failed:\n{}", bad.join("\n"));
        }
        Ok(lines)
    }
}

fn as_text(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Number(n) => {
            let f = n.as_f64().unwrap_or(0.0);
            if f.fract() == 0.0 && f.abs() < 1e15 { format!("{}", f as i64) } else { format!("{f}") }
        }
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn filters() {
        let mut f = Facts::new();
        f.set("ha", 26_642_264.3, "t");
        f.set("n", 37506, "t");
        f.set("d", "2025-09-23T14:17:09Z", "t");
        assert_eq!(f.render("{ha|div:1e6|dec:1} MILLONES").unwrap(), "26,6 MILLONES");
        assert_eq!(f.render("{n|int} FOCOS").unwrap(), "37.506 FOCOS");
        assert_eq!(f.render("{d|ddmmyyyy}").unwrap(), "23/09/2025");
        assert_eq!(f.render("{d|mon_es}").unwrap(), "SEP 2025");
        assert_eq!(Facts::literal_part("CASI {x} VECES 7"), "CASI  VECES 7");
    }
}
