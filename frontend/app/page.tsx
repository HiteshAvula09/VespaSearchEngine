"use client";

import { FormEvent, useState } from "react";

type Result = {
  doc_id: string;
  source: string;
  source_type: string;
  title: string;
  content: string;
  url: string;
  relevance: number;
};

type SearchResponse = {
  answer: string | null;
  results: Result[];
};

const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [source, setSource] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();

    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setData(null);

    try {
      const response = await fetch(`${API}/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          mode,
          source: source || null,
          hits: 5,
          generate: true,
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const responseData: SearchResponse =
        await response.json();

      setData(responseData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : String(err)
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="hero">
        <div className="brandRow">
          <div className="mark">V</div>

          <div>
            <div className="brand">VespaSearch</div>

            <div className="subbrand">
              Enterprise Knowledge base
            </div>
          </div>
        </div>

        <h1 style={{ marginBottom: "20px" }}>
          Search across your workspace.
        </h1>

        <form
          onSubmit={submit}
          className="searchPanel"
        >
          <textarea
            value={query}
            onChange={(event) =>
              setQuery(event.target.value)
            }
            placeholder="What decisions were made about Project Orion?"
            rows={3}
          />

          <div className="controls">
            <select
              value={mode}
              onChange={(event) =>
                setMode(event.target.value)
              }
            >
              <option value="hybrid">
                Hybrid
              </option>

              <option value="bm25">
                BM25
              </option>

              <option value="semantic">
                Semantic
              </option>
            </select>

            <select
              value={source}
              onChange={(event) =>
                setSource(event.target.value)
              }
            >
              <option value="">
                All sources
              </option>

              <option value="slack">
                Slack
              </option>

              <option value="google_drive">
                Google Drive
              </option>

              <option value="github">
                GitHub
              </option>
            </select>

            <button
              type="submit"
              disabled={loading}
            >
              {loading
                ? "Searching..."
                : "Search"}
            </button>
          </div>
        </form>

        {error && (
          <div className="error">
            {error}
          </div>
        )}
      </section>

      {data && (
        <section className="resultsWrap">
          {data.answer && (
            <article className="answerCard">
              <div className="eyebrow">
                Grounded answer
              </div>

              <div className="answer">
                {data.answer}
              </div>
            </article>
          )}

          <div className="sectionTitle">
            Retrieved evidence
          </div>

          {data.results.length === 0 ? (
            <div className="error">
              No results found.
            </div>
          ) : (
            <div className="cards">
              {data.results.map(
                (result, index) => (
                  <article
                    className="resultCard"
                    key={`${result.doc_id}-${index}`}
                  >
                    <div className="resultTop">
                      <span className="badge">
                        {result.source.replace(
                          "_",
                          " "
                        )}
                      </span>

                      <span className="score">
                        {Number(
                          result.relevance || 0
                        ).toFixed(3)}
                      </span>
                    </div>

                    <h3>
                      [{index + 1}]{" "}
                      {result.title ||
                        "Untitled"}
                    </h3>

                    <p>
                      {result.content}
                    </p>
                  </article>
                )
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}