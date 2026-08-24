import { useState, useRef, useEffect } from "react";

const API = "http://localhost:8000/v1";

const COLORS = {
  bg:        "#0F1117",
  surface:   "#161B22",
  card:      "#1C2128",
  border:    "#30363D",
  accent:    "#58A6FF",
  accentDim: "#1F3A5C",
  green:     "#3FB950",
  greenDim:  "#1A3A22",
  red:       "#F78166",
  redDim:    "#3A1A1A",
  textPri:   "#E6EDF3",
  textSec:   "#C9D1D9",
  textMuted: "#7D8590",
  mono:      "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
  sans:      "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
};

// ── Animated confidence bar ──────────────────────────────────────────────────
function ConfidenceBar({ score }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setWidth(score * 100), 80);
    return () => clearTimeout(t);
  }, [score]);

  const color = score >= 0.7 ? COLORS.green : score >= 0.5 ? COLORS.accent : COLORS.red;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{
        flex: 1, height: 3, background: COLORS.border, borderRadius: 99, overflow: "hidden"
      }}>
        <div style={{
          height: "100%", width: `${width}%`, background: color,
          borderRadius: 99, transition: "width 0.6s cubic-bezier(0.4,0,0.2,1)"
        }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: COLORS.mono, color, minWidth: 36, textAlign: "right" }}>
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
}

// ── Source evidence card ──────────────────────────────────────────────────────
function SourceCard({ text, score, index }) {
  const [open, setOpen] = useState(false);
  const preview = text.trim().slice(0, 120) + (text.length > 120 ? "…" : "");

  return (
    <div style={{
      border: `1px solid ${COLORS.border}`, borderRadius: 8,
      overflow: "hidden", background: COLORS.surface, marginTop: 6
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: "100%", padding: "8px 12px", background: "transparent",
          border: "none", cursor: "pointer", textAlign: "left",
          display: "flex", flexDirection: "column", gap: 5
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 11, fontFamily: COLORS.mono, color: COLORS.textMuted }}>
            SOURCE {index + 1}
          </span>
          <span style={{ fontSize: 11, color: COLORS.textMuted }}>
            {open ? "▲ collapse" : "▼ expand"}
          </span>
        </div>
        <ConfidenceBar score={score} />
        {!open && (
          <p style={{
            margin: 0, fontSize: 12, color: COLORS.textMuted,
            fontFamily: COLORS.sans, lineHeight: 1.5
          }}>
            {preview}
          </p>
        )}
      </button>

      {open && (
        <div style={{
          padding: "0 12px 12px", borderTop: `1px solid ${COLORS.border}`,
          marginTop: 0
        }}>
          <p style={{
            margin: "10px 0 0", fontSize: 12.5, color: COLORS.textSec,
            fontFamily: COLORS.sans, lineHeight: 1.7, whiteSpace: "pre-wrap"
          }}>
            {text.trim()}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────
function Message({ msg }) {
  const [showSources, setShowSources] = useState(false);

  return (
    <div style={{ marginBottom: 24 }}>
      {/* Question */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <div style={{
          maxWidth: "75%", padding: "10px 14px",
          background: COLORS.accentDim, border: `1px solid ${COLORS.accent}33`,
          borderRadius: "12px 12px 2px 12px",
          fontSize: 14, color: COLORS.textPri, fontFamily: COLORS.sans, lineHeight: 1.5
        }}>
          {msg.question}
        </div>
      </div>

      {/* Answer */}
      <div style={{ display: "flex", justifyContent: "flex-start" }}>
        <div style={{ maxWidth: "85%" }}>
          {msg.error ? (
            <div style={{
              padding: "10px 14px", background: COLORS.redDim,
              border: `1px solid ${COLORS.red}44`, borderRadius: "2px 12px 12px 12px",
              fontSize: 13, color: COLORS.red, fontFamily: COLORS.sans
            }}>
              ⚠ {msg.error}
            </div>
          ) : (
            <div>
              {/* Answer text */}
              <div style={{
                padding: "12px 16px",
                background: msg.grounded ? COLORS.card : COLORS.redDim,
                border: `1px solid ${msg.grounded ? COLORS.border : COLORS.red + "44"}`,
                borderRadius: "2px 12px 12px 12px",
              }}>
                {/* Grounded badge */}
                <div style={{
                  display: "inline-flex", alignItems: "center", gap: 5,
                  padding: "2px 8px", borderRadius: 99, marginBottom: 8,
                  background: msg.grounded ? COLORS.greenDim : COLORS.redDim,
                  border: `1px solid ${msg.grounded ? COLORS.green + "55" : COLORS.red + "55"}`,
                  fontSize: 10, fontFamily: COLORS.mono,
                  color: msg.grounded ? COLORS.green : COLORS.red,
                }}>
                  <span style={{
                    width: 5, height: 5, borderRadius: "50%",
                    background: msg.grounded ? COLORS.green : COLORS.red,
                    display: "inline-block"
                  }} />
                  {msg.grounded ? "GROUNDED" : "NOT GROUNDED"}
                </div>

                <p style={{
                  margin: 0, fontSize: 14, color: COLORS.textPri,
                  fontFamily: COLORS.sans, lineHeight: 1.7
                }}>
                  {msg.answer}
                </p>
              </div>

              {/* Meta row */}
              <div style={{
                display: "flex", alignItems: "center",
                justifyContent: "space-between", marginTop: 6, padding: "0 2px"
              }}>
                <div style={{ display: "flex", gap: 12 }}>
                  <span style={{ fontSize: 11, fontFamily: COLORS.mono, color: COLORS.textMuted }}>
                    {msg.latency}ms
                  </span>
                  {msg.sources?.length > 0 && (
                    <span style={{ fontSize: 11, fontFamily: COLORS.mono, color: COLORS.textMuted }}>
                      {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                {msg.sources?.length > 0 && (
                  <button
                    onClick={() => setShowSources(s => !s)}
                    style={{
                      background: "none", border: `1px solid ${COLORS.border}`,
                      borderRadius: 6, padding: "2px 10px", cursor: "pointer",
                      fontSize: 11, color: COLORS.textMuted, fontFamily: COLORS.sans
                    }}
                  >
                    {showSources ? "Hide sources" : "View sources"}
                  </button>
                )}
              </div>

              {/* Source cards */}
              {showSources && msg.sources?.map((src, i) => (
                <SourceCard
                  key={i}
                  text={src}
                  score={msg.similarity_scores[i]}
                  index={i}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [health, setHealth]         = useState(null);
  const [ingestPath, setIngestPath] = useState("sample_docs/ml_basics.txt");
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestResult, setIngestResult]   = useState(null);
  const [messages, setMessages]     = useState([]);
  const [question, setQuestion]     = useState("");
  const [queryLoading, setQueryLoading] = useState(false);
  const [topK, setTopK]             = useState(3);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  const fetchHealth = async () => {
    try {
      const res  = await fetch(`${API}/health`);
      const data = await res.json();
      setHealth(data);
    } catch {
      setHealth({ status: "offline", chunks_stored: 0 });
    }
  };

  useEffect(() => { fetchHealth(); }, []);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, queryLoading]);

  const handleIngest = async () => {
    if (!ingestPath.trim() || ingestLoading) return;
    setIngestLoading(true);
    setIngestResult(null);
    try {
      const res  = await fetch(`${API}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: ingestPath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ingestion failed");
      setIngestResult({ success: true, ...data });
      fetchHealth();
    } catch (e) {
      setIngestResult({ success: false, error: e.message });
    }
    setIngestLoading(false);
  };

  const handleQuery = async () => {
    if (!question.trim() || queryLoading) return;
    const q = question;
    setQuestion("");
    setQueryLoading(true);
    const start = Date.now();
    try {
      const res  = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, top_k: topK }),
      });
      const data = await res.json();
      const latency = Date.now() - start;
      if (!res.ok) throw new Error(data.detail || "Query failed");
      setMessages(prev => [...prev, { question: q, latency, ...data }]);
    } catch (e) {
      setMessages(prev => [...prev, { question: q, error: e.message }]);
    }
    setQueryLoading(false);
    fetchHealth();
    inputRef.current?.focus();
  };

  const handleClear = async () => {
    if (!window.confirm("Clear all ingested data and conversation?")) return;
    await fetch(`${API}/collection`, { method: "DELETE" });
    setMessages([]);
    setIngestResult(null);
    fetchHealth();
  };

  const isOnline = health?.status === "ok";

  return (
    <div style={{
      minHeight: "100vh", background: COLORS.bg,
      fontFamily: COLORS.sans, color: COLORS.textPri,
      display: "flex", flexDirection: "column"
    }}>

      {/* ── Header ─────────────────────────────────────────────────── */}
      <header style={{
        padding: "0 24px", height: 52,
        borderBottom: `1px solid ${COLORS.border}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: COLORS.surface, flexShrink: 0,
        position: "sticky", top: 0, zIndex: 10
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: COLORS.textPri }}>
            RAG QA
          </span>
          <span style={{ color: COLORS.border }}>·</span>
          <span style={{ fontSize: 12, color: COLORS.textMuted, fontFamily: COLORS.mono }}>
            Document Intelligence API
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {health && (
            <span style={{ fontSize: 12, fontFamily: COLORS.mono, color: COLORS.textMuted }}>
              <span style={{
                display: "inline-block", width: 6, height: 6, borderRadius: "50%",
                background: isOnline ? COLORS.green : COLORS.red,
                marginRight: 6, verticalAlign: "middle"
              }} />
              {isOnline
                ? `${health.chunks_stored} chunks stored`
                : "API offline"}
            </span>
          )}
          <button
            onClick={fetchHealth}
            style={{
              background: "none", border: `1px solid ${COLORS.border}`,
              borderRadius: 6, padding: "4px 10px", cursor: "pointer",
              fontSize: 11, color: COLORS.textMuted, fontFamily: COLORS.mono
            }}
          >
            Refresh
          </button>
        </div>
      </header>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* ── Left panel ─────────────────────────────────────────────── */}
        <aside style={{
          width: 280, flexShrink: 0,
          borderRight: `1px solid ${COLORS.border}`,
          background: COLORS.surface,
          display: "flex", flexDirection: "column",
          padding: 20, gap: 20, overflowY: "auto"
        }}>

          {/* Ingest */}
          <div>
            <div style={{
              fontSize: 10, fontFamily: COLORS.mono, color: COLORS.textMuted,
              letterSpacing: "0.08em", marginBottom: 10
            }}>
              DOCUMENT
            </div>

            <input
              value={ingestPath}
              onChange={e => setIngestPath(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleIngest()}
              placeholder="Path to .txt or .md file"
              style={{
                width: "100%", padding: "8px 10px", boxSizing: "border-box",
                background: COLORS.card, border: `1px solid ${COLORS.border}`,
                borderRadius: 6, color: COLORS.textPri, fontSize: 12,
                fontFamily: COLORS.mono, outline: "none", marginBottom: 8
              }}
            />

            <button
              onClick={handleIngest}
              disabled={ingestLoading || !ingestPath.trim()}
              style={{
                width: "100%", padding: "8px 0",
                background: ingestLoading ? COLORS.border : COLORS.accent,
                border: "none", borderRadius: 6, cursor: ingestLoading ? "not-allowed" : "pointer",
                color: ingestLoading ? COLORS.textMuted : "#fff",
                fontSize: 13, fontWeight: 500, transition: "opacity 0.15s"
              }}
            >
              {ingestLoading ? "Ingesting…" : "Ingest document"}
            </button>

            {ingestResult && (
              <div style={{
                marginTop: 8, padding: "8px 10px", borderRadius: 6, fontSize: 12,
                background: ingestResult.success ? COLORS.greenDim : COLORS.redDim,
                border: `1px solid ${ingestResult.success ? COLORS.green + "44" : COLORS.red + "44"}`,
                color: ingestResult.success ? COLORS.green : COLORS.red,
                fontFamily: COLORS.mono
              }}>
                {ingestResult.success
                  ? `✓ ${ingestResult.chunks_stored} chunks stored`
                  : `✗ ${ingestResult.error}`}
              </div>
            )}
          </div>

          {/* Divider */}
          <div style={{ height: 1, background: COLORS.border }} />

          {/* Settings */}
          <div>
            <div style={{
              fontSize: 10, fontFamily: COLORS.mono, color: COLORS.textMuted,
              letterSpacing: "0.08em", marginBottom: 10
            }}>
              RETRIEVAL SETTINGS
            </div>

            <label style={{ fontSize: 12, color: COLORS.textMuted, display: "block", marginBottom: 6 }}>
              Top-K chunks: <span style={{ color: COLORS.accent, fontFamily: COLORS.mono }}>{topK}</span>
            </label>
            <input
              type="range" min={1} max={8} value={topK}
              onChange={e => setTopK(Number(e.target.value))}
              style={{ width: "100%", accentColor: COLORS.accent }}
            />
            <div style={{
              display: "flex", justifyContent: "space-between",
              fontSize: 10, color: COLORS.textMuted, fontFamily: COLORS.mono, marginTop: 2
            }}>
              <span>1</span><span>8</span>
            </div>
            <p style={{ fontSize: 11, color: COLORS.textMuted, margin: "8px 0 0", lineHeight: 1.5 }}>
              Higher = more context retrieved. Lower = more precise.
            </p>
          </div>

          {/* Divider */}
          <div style={{ height: 1, background: COLORS.border }} />

          {/* Stats */}
          <div>
            <div style={{
              fontSize: 10, fontFamily: COLORS.mono, color: COLORS.textMuted,
              letterSpacing: "0.08em", marginBottom: 10
            }}>
              SESSION
            </div>

            {[
              ["Chunks stored", health?.chunks_stored ?? "—"],
              ["Questions asked", messages.filter(m => !m.error).length],
              ["Grounded answers", messages.filter(m => m.grounded).length],
              ["Avg latency", messages.filter(m => m.latency).length > 0
                ? Math.round(messages.filter(m => m.latency).reduce((a, m) => a + m.latency, 0) / messages.filter(m => m.latency).length) + "ms"
                : "—"],
            ].map(([label, val]) => (
              <div key={label} style={{
                display: "flex", justifyContent: "space-between",
                alignItems: "baseline", marginBottom: 8
              }}>
                <span style={{ fontSize: 12, color: COLORS.textMuted }}>{label}</span>
                <span style={{ fontSize: 13, fontFamily: COLORS.mono, color: COLORS.textPri }}>{val}</span>
              </div>
            ))}
          </div>

          {/* Clear */}
          <div style={{ marginTop: "auto" }}>
            <button
              onClick={handleClear}
              style={{
                width: "100%", padding: "7px 0",
                background: "transparent", border: `1px solid ${COLORS.border}`,
                borderRadius: 6, cursor: "pointer",
                fontSize: 12, color: COLORS.textMuted,
                transition: "border-color 0.15s, color 0.15s"
              }}
              onMouseEnter={e => { e.target.style.borderColor = COLORS.red; e.target.style.color = COLORS.red; }}
              onMouseLeave={e => { e.target.style.borderColor = COLORS.border; e.target.style.color = COLORS.textMuted; }}
            >
              Clear all data
            </button>
          </div>
        </aside>

        {/* ── Conversation ────────────────────────────────────────────── */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {/* Messages area */}
          <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>

            {messages.length === 0 && !queryLoading && (
              <div style={{
                height: "100%", display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center", gap: 12
              }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12,
                  background: COLORS.accentDim, border: `1px solid ${COLORS.accent}33`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 22
                }}>
                  🔍
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 15, fontWeight: 500, color: COLORS.textPri, marginBottom: 6 }}>
                    Ask anything about your document
                  </div>
                  <div style={{ fontSize: 13, color: COLORS.textMuted }}>
                    Ingest a document on the left, then ask questions here.
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap", justifyContent: "center" }}>
                  {["What is overfitting?", "Explain precision vs recall", "What is data leakage?"].map(s => (
                    <button
                      key={s}
                      onClick={() => setQuestion(s)}
                      style={{
                        padding: "6px 14px", background: COLORS.card,
                        border: `1px solid ${COLORS.border}`, borderRadius: 99,
                        cursor: "pointer", fontSize: 12, color: COLORS.textMuted
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => <Message key={i} msg={msg} />)}

            {queryLoading && (
              <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 24 }}>
                <div style={{
                  padding: "12px 16px", background: COLORS.card,
                  border: `1px solid ${COLORS.border}`, borderRadius: "2px 12px 12px 12px",
                  display: "flex", gap: 5, alignItems: "center"
                }}>
                  {[0, 150, 300].map(d => (
                    <span key={d} style={{
                      width: 6, height: 6, borderRadius: "50%",
                      background: COLORS.accent, display: "inline-block",
                      animation: "pulse 1s infinite",
                      animationDelay: `${d}ms`
                    }} />
                  ))}
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div style={{
            padding: "16px 32px",
            borderTop: `1px solid ${COLORS.border}`,
            background: COLORS.surface,
            display: "flex", gap: 10, alignItems: "flex-end"
          }}>
            <textarea
              ref={inputRef}
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleQuery();
                }
              }}
              placeholder="Ask a question about your document…"
              rows={1}
              style={{
                flex: 1, padding: "10px 14px", resize: "none", overflow: "hidden",
                background: COLORS.card, border: `1px solid ${COLORS.border}`,
                borderRadius: 8, color: COLORS.textPri, fontSize: 14,
                fontFamily: COLORS.sans, outline: "none", lineHeight: 1.5,
                transition: "border-color 0.15s",
              }}
              onFocus={e => e.target.style.borderColor = COLORS.accent + "88"}
              onBlur={e  => e.target.style.borderColor = COLORS.border}
            />
            <button
              onClick={handleQuery}
              disabled={queryLoading || !question.trim()}
              style={{
                padding: "10px 20px", height: 42,
                background: queryLoading || !question.trim() ? COLORS.card : COLORS.accent,
                border: `1px solid ${queryLoading || !question.trim() ? COLORS.border : COLORS.accent}`,
                borderRadius: 8, cursor: queryLoading || !question.trim() ? "not-allowed" : "pointer",
                color: queryLoading || !question.trim() ? COLORS.textMuted : "#fff",
                fontSize: 14, fontWeight: 500, transition: "all 0.15s", whiteSpace: "nowrap"
              }}
            >
              Ask →
            </button>
          </div>
        </main>
      </div>

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: ${COLORS.bg}; }
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${COLORS.border}; border-radius: 99px; }
        input::placeholder, textarea::placeholder { color: ${COLORS.textMuted}; }
      `}</style>
    </div>
  );
}
