"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import VoiceSearchPanel from "./components/VoiceSearchPanel";


type User = {
  username: string;
  role: string;
};


type Result = {
  doc_id: string;
  source: string;
  source_type: string;
  title: string;
  content: string;
  url: string;
  file_location: string;
  access: "full" | "restricted";
  message?: string;
  relevance: number;
};


type SearchResponse = {
  answer: string | null;
  user: User;
  results: Result[];
};


const API =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";


export default function Home() {

  const [user, setUser] =
    useState<User | null>(null);

  const [
    checkingSession,
    setCheckingSession,
  ] = useState(true);

  const [username, setUsername] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [loginError, setLoginError] =
    useState("");

  const [query, setQuery] =
    useState("");

  const [mode, setMode] =
    useState("hybrid");

  const [source, setSource] =
    useState("");

  const [data, setData] =
    useState<SearchResponse | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  /*
   * --------------------------------------------------
   * LOAD EXISTING LOGIN SESSION
   * --------------------------------------------------
   */

  useEffect(() => {

    async function loadSession() {

      try {

        const response =
          await fetch(
            `${API}/auth/me`,
            {
              credentials: "include",
            }
          );

        if (response.ok) {

          setUser(
            await response.json()
          );

        }

      } finally {

        setCheckingSession(false);

      }
    }

    loadSession();

  }, []);


  /*
   * --------------------------------------------------
   * LOGIN
   * --------------------------------------------------
   */

  async function login(
    event: FormEvent
  ) {

    event.preventDefault();

    setLoginError("");

    try {

      const response =
        await fetch(
          `${API}/auth/login`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            credentials:
              "include",

            body: JSON.stringify({
              username,
              password,
            }),
          }
        );

      if (!response.ok) {

        const body =
          await response
            .json()
            .catch(() => null);

        throw new Error(
          body?.detail ||
          "Login failed."
        );

      }

      const loggedIn =
        await response.json();

      setUser(loggedIn);

      setPassword("");

    } catch (err) {

      setLoginError(
        err instanceof Error
          ? err.message
          : String(err)
      );

    }
  }


  /*
   * --------------------------------------------------
   * LOGOUT
   * --------------------------------------------------
   */

  async function logout() {

    await fetch(
      `${API}/auth/logout`,
      {
        method: "POST",
        credentials: "include",
      }
    );

    setUser(null);
    setData(null);
    setQuery("");
    setUsername("");
    setPassword("");
  }


  /*
   * --------------------------------------------------
   * SHARED SEARCH FUNCTION
   *
   * BOTH:
   *
   * typed query
   * voice query
   *
   * use this exact function.
   * --------------------------------------------------
   */

  const runSearch = useCallback(
    async (
      searchQuery: string
    ) => {

      const cleaned =
        searchQuery.trim();

      if (!cleaned) {
        return;
      }

      setLoading(true);
      setError("");
      setData(null);

      try {

        const response =
          await fetch(
            `${API}/search`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              credentials:
                "include",

              body: JSON.stringify({
                query: cleaned,
                mode,
                source:
                  source || null,
                hits: 5,
                generate: true,
              }),
            }
          );

        if (
          response.status === 401
        ) {

          setUser(null);

          throw new Error(
            "Your session expired. " +
            "Please sign in again."
          );

        }

        if (!response.ok) {

          throw new Error(
            await response.text()
          );

        }

        const result =
          await response.json();

        setData(result);

      } catch (err) {

        setError(
          err instanceof Error
            ? err.message
            : String(err)
        );

      } finally {

        setLoading(false);

      }

    },
    [
      mode,
      source,
    ]
  );


  /*
   * --------------------------------------------------
   * TEXT SEARCH
   * --------------------------------------------------
   */

  async function submit(
    event: FormEvent
  ) {

    event.preventDefault();

    await runSearch(query);
  }


  /*
   * --------------------------------------------------
   * VOICE SEARCH
   *
   * LiveKit transcription arrives here.
   *
   * 1. Put speech into search box.
   * 2. Run EXACT SAME /search request.
   * --------------------------------------------------
   */

  const handleVoiceQuery =
    useCallback(
      async (
        voiceQuery: string
      ) => {

        const cleaned =
          voiceQuery.trim();

        if (!cleaned) {
          return;
        }

        console.log(
          "Running voice search:",
          cleaned
        );

        /*
         * Show spoken words in textarea.
         */
        setQuery(cleaned);

        /*
         * Same search as typed query.
         */
        await runSearch(cleaned);

      },
      [runSearch]
    );


  /*
   * --------------------------------------------------
   * SESSION CHECK
   * --------------------------------------------------
   */

  if (checkingSession) {

    return (

      <main className="loginShell">

        <div className="loginCard">
          Checking session...
        </div>

      </main>

    );
  }


  /*
   * --------------------------------------------------
   * LOGIN PAGE
   * --------------------------------------------------
   */

  if (!user) {

    return (

      <main className="loginShell">

        <section className="loginCard">

          <div
            className="brandRow compactBrand"
          >

            <div className="mark">
              V
            </div>

            <div>

              <div className="brand">
                VespaSearch
              </div>

              <div className="subbrand">
                Enterprise Knowledge Base
              </div>

            </div>

          </div>


          <h2>
            Sign in to search
          </h2>


          <form
            onSubmit={login}
            className="loginForm"
          >

            <label>

              Username

              <input
                value={username}
                onChange={(event) =>
                  setUsername(
                    event.target.value
                  )
                }
                autoComplete="username"
                required
              />

            </label>


            <label>

              Password

              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value
                  )
                }
                autoComplete=
                  "current-password"
                required
              />

            </label>


            <button type="submit">
              Login
            </button>

          </form>


          {loginError && (

            <div className="error">
              {loginError}
            </div>

          )}

        </section>

      </main>

    );
  }


  /*
   * --------------------------------------------------
   * MAIN SEARCH PAGE
   * --------------------------------------------------
   */

  return (

    <main>

      <section className="hero">

        {/* HEADER */}

        <div className="topBar">

          <div
            className="brandRow topBrand"
          >

            <div className="mark">
              V
            </div>

            <div>

              <div className="brand">
                VespaSearch
              </div>

              <div className="subbrand">
                Enterprise Knowledge Base
              </div>

            </div>

          </div>


          <div className="userPanel">

            <div>

              <div
                className="signedInLabel"
              >
                Logged in as
              </div>

              <div
                className="signedInUser"
              >
                {user.username}
              </div>

            </div>


            <button
              className="logoutButton"
              onClick={logout}
              type="button"
            >
              Logout
            </button>

          </div>

        </div>


        <h1
          style={{
            marginBottom: "20px",
          }}
        >
          Search across your workspace.
        </h1>


        {/* SEARCH FORM */}

        <form
          onSubmit={submit}
          className="searchPanel"
        >

          <textarea
            value={query}
            onChange={(event) =>
              setQuery(
                event.target.value
              )
            }
            placeholder=
              "Search Slack, Google Drive, and GitHub..."
            rows={3}
          />


          <div className="controls">

            {/* SEARCH MODE */}

            <select
              value={mode}
              onChange={(event) =>
                setMode(
                  event.target.value
                )
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


            {/* SOURCE */}

            <select
              value={source}
              onChange={(event) =>
                setSource(
                  event.target.value
                )
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


            {/* VOICE SEARCH */}

            <VoiceSearchPanel
              onVoiceQuery={
                handleVoiceQuery
              }
              disabled={loading}
            />


            {/* TEXT SEARCH */}

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


        {/* SEARCH ERROR */}

        {error && (

          <div className="error">
            {error}
          </div>

        )}

      </section>


      {/* --------------------------------------------------
          SEARCH RESULTS
         -------------------------------------------------- */}

      {data && (

        <section
          className="resultsWrap"
        >

          {/* GROUNDED ANSWER */}

          {data.answer && (

            <article
              className="answerCard"
            >

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
                (
                  result,
                  index
                ) => {

                  const restricted =
                    result.access ===
                    "restricted";

                  return (

                    <article
                      className={
                        `resultCard ${
                          restricted
                            ? "restrictedCard"
                            : ""
                        }`
                      }
                      key={
                        `${result.doc_id}-${index}`
                      }
                    >

                      {/* HEADER */}

                      <div
                        className="resultTop"
                      >

                        <span
                          className="badge"
                        >
                          {result.source.replace(
                            "_",
                            " "
                          )}
                        </span>

                        <span
                          className="score"
                        >
                          {Number(
                            result.relevance ||
                            0
                          ).toFixed(3)}
                        </span>

                      </div>


                      {/* TITLE */}

                      <h3>

                        [{index + 1}]{" "}

                        {result.title ||
                          "Untitled"}

                      </h3>


                      {/* RESTRICTED */}

                      {restricted ? (

                        <div
                          className=
                            "restrictedBody"
                        >

                          <div
                            className=
                              "restrictedLabel"
                          >
                            🔒 Limited Role View
                          </div>

                          <p>
                            Your role can see
                            that this result
                            exists and where
                            it is located, but
                            cannot view its
                            contents or link.
                          </p>


                          <div
                            className=
                              "locationBox"
                          >

                            <span>
                              Location
                            </span>

                            <strong>
                              {
                                result.file_location ||
                                result.source
                              }
                            </strong>

                          </div>

                        </div>

                      ) : (

                        /* FULL ACCESS */

                        <>

                          <p>
                            {result.content}
                          </p>


                          {result.file_location && (

                            <div
                              className=
                                "fileLocation"
                            >
                              Location:{" "}
                              {
                                result.file_location
                              }
                            </div>

                          )}


                          {result.url && (

                            <a
                              href={
                                result.url
                              }
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open source
                            </a>

                          )}

                        </>

                      )}

                    </article>

                  );
                }
              )}

            </div>

          )}

        </section>

      )}

    </main>
  );
}