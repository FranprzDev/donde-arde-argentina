//! A tiny arithmetic expression language for time marks in `story.toml`:
//! numbers, identifiers, `+ - * /`, parentheses, unary minus and the functions `max(a, b, ...)`, `min(...)`, `round(x)`.
//! `resolve` evaluates a set of named expressions in dependency order (the order in the file does not matter) and reports
//! unknown names and cycles.
use anyhow::{Result, anyhow, bail};
use indexmap::IndexMap;

#[derive(Debug, Clone, PartialEq)]
enum Tok {
    Num(f64),
    Id(String),
    Op(char),
}

fn lex(s: &str) -> Result<Vec<Tok>> {
    let c: Vec<char> = s.chars().collect();
    let mut i = 0;
    let mut out = vec![];
    while i < c.len() {
        let ch = c[i];
        if ch.is_whitespace() {
            i += 1;
        } else if ch.is_ascii_digit() || (ch == '.' && i + 1 < c.len() && c[i + 1].is_ascii_digit()) {
            let st = i;
            while i < c.len() && (c[i].is_ascii_digit() || c[i] == '.' || c[i] == 'e' || ((c[i] == '-' || c[i] == '+') && c[i - 1] == 'e')) {
                i += 1;
            }
            let t: String = c[st..i].iter().collect();
            out.push(Tok::Num(t.parse().map_err(|_| anyhow!("bad number '{t}' in '{s}'"))?));
        } else if ch.is_alphabetic() || ch == '_' {
            let st = i;
            while i < c.len() && (c[i].is_alphanumeric() || c[i] == '_' || c[i] == '.') {
                i += 1;
            }
            out.push(Tok::Id(c[st..i].iter().collect()));
        } else if "+-*/(),".contains(ch) {
            out.push(Tok::Op(ch));
            i += 1;
        } else {
            bail!("unexpected '{ch}' in expression '{s}'");
        }
    }
    Ok(out)
}

struct P<'a, F: Fn(&str) -> Option<f64>> {
    t: &'a [Tok],
    i: usize,
    look: &'a F,
    src: &'a str,
}

impl<F: Fn(&str) -> Option<f64>> P<'_, F> {
    fn peek(&self) -> Option<&Tok> {
        self.t.get(self.i)
    }
    fn expr(&mut self) -> Result<f64> {
        let mut v = self.term()?;
        while let Some(Tok::Op(o @ ('+' | '-'))) = self.peek().cloned() {
            self.i += 1;
            let r = self.term()?;
            v = if o == '+' { v + r } else { v - r };
        }
        Ok(v)
    }
    fn term(&mut self) -> Result<f64> {
        let mut v = self.unary()?;
        while let Some(Tok::Op(o @ ('*' | '/'))) = self.peek().cloned() {
            self.i += 1;
            let r = self.unary()?;
            v = if o == '*' { v * r } else { v / r };
        }
        Ok(v)
    }
    fn unary(&mut self) -> Result<f64> {
        if let Some(Tok::Op('-')) = self.peek() {
            self.i += 1;
            return Ok(-self.unary()?);
        }
        self.atom()
    }
    fn atom(&mut self) -> Result<f64> {
        match self.peek().cloned() {
            Some(Tok::Num(n)) => {
                self.i += 1;
                Ok(n)
            }
            Some(Tok::Op('(')) => {
                self.i += 1;
                let v = self.expr()?;
                self.expect(')')?;
                Ok(v)
            }
            Some(Tok::Id(name)) => {
                self.i += 1;
                if let Some(Tok::Op('(')) = self.peek() {
                    self.i += 1;
                    let mut args = vec![self.expr()?];
                    while let Some(Tok::Op(',')) = self.peek() {
                        self.i += 1;
                        args.push(self.expr()?);
                    }
                    self.expect(')')?;
                    return match name.as_str() {
                        "max" => Ok(args.iter().cloned().fold(f64::MIN, f64::max)),
                        "min" => Ok(args.iter().cloned().fold(f64::MAX, f64::min)),
                        "round" => Ok(args[0].round()),
                        _ => bail!("unknown function '{name}' in '{}'", self.src),
                    };
                }
                (self.look)(&name).ok_or_else(|| anyhow!("UNRESOLVED:{name}"))
            }
            other => bail!("unexpected {other:?} in '{}'", self.src),
        }
    }
    fn expect(&mut self, c: char) -> Result<()> {
        if self.peek() == Some(&Tok::Op(c)) {
            self.i += 1;
            Ok(())
        } else {
            bail!("expected '{c}' in '{}'", self.src)
        }
    }
}

/// Evaluate one expression; `look` resolves identifiers.
pub fn eval(src: &str, look: &impl Fn(&str) -> Option<f64>) -> Result<f64> {
    let t = lex(src)?;
    let mut p = P { t: &t, i: 0, look, src };
    let v = p.expr()?;
    if p.i != t.len() {
        bail!("trailing tokens in '{src}'");
    }
    Ok(v)
}

/// Resolve every named expression of `defs` (which may reference each other and the `known` values).
pub fn resolve(defs: &IndexMap<String, String>, known: &IndexMap<String, f64>) -> Result<IndexMap<String, f64>> {
    let mut out: IndexMap<String, f64> = known.clone();
    let mut left: Vec<(&String, &String)> = defs.iter().collect();
    while !left.is_empty() {
        let before = left.len();
        let mut still = vec![];
        let mut last_err = String::new();
        for (k, e) in left {
            match eval(e, &|n: &str| out.get(n).copied()) {
                Ok(v) => {
                    out.insert(k.clone(), v);
                }
                Err(err) => {
                    let m = err.to_string();
                    if !m.starts_with("UNRESOLVED:") {
                        bail!("mark '{k}': {m}");
                    }
                    last_err = format!("mark '{k}' = '{e}' needs '{}'", &m[11..]);
                    still.push((k, e));
                }
            }
        }
        if still.len() == before {
            bail!("time marks cannot be resolved (unknown name or cycle): {last_err}");
        }
        left = still;
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn evaluates_in_any_order() {
        let mut d = IndexMap::new();
        d.insert("b".to_string(), "a + 2 * (c - 1)".to_string());
        d.insert("a".to_string(), "max(1, 3) - 0.5".to_string());
        d.insert("c".to_string(), "-x".to_string());
        let mut k = IndexMap::new();
        k.insert("x".to_string(), -4.0);
        let r = resolve(&d, &k).unwrap();
        assert_eq!(r["a"], 2.5);
        assert_eq!(r["b"], 8.5);
    }
    #[test]
    fn reports_cycles() {
        let mut d = IndexMap::new();
        d.insert("a".to_string(), "b".to_string());
        d.insert("b".to_string(), "a".to_string());
        assert!(resolve(&d, &IndexMap::new()).is_err());
    }
}
