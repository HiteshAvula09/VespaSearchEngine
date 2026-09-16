"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  BarVisualizer,
  RoomAudioRenderer,
  SessionProvider,
  useAgent,
  useSession,
  useTranscriptions,
} from "@livekit/components-react";

import {
  TokenSource,
} from "livekit-client";

import "@livekit/components-styles";


const AGENT_NAME =
  process.env.NEXT_PUBLIC_LIVEKIT_AGENT_NAME ||
  "vespa-search-voice";


type VoiceResult = {
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

type VoiceSearchResponse = {
  answer: string | null;
  results: VoiceResult[];
};

type VoiceSearchPanelProps = {
  onVoiceQuery: (query: string) => void;
  disabled?: boolean;
  searchData?: VoiceSearchResponse | null;
  searchLoading?: boolean;
  searchError?: string;
};


/*
 * --------------------------------------------------
 * END-SESSION DETECTION
 * --------------------------------------------------
 *
 * These phrases should NOT be sent to Vespa.
 *
 * Examples:
 *
 * "thank you"
 * "thanks"
 * "thank you that's it"
 * "that's all thank you"
 * "thanks that's all"
 * "thank you I'm done"
 */
function isEndSessionPhrase(
  text: string
): boolean {

  const normalized = text
    .toLowerCase()
    .replace(/[.,!?;:'"]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  /*
   * Direct short phrases.
   */
  const exactPhrases = new Set([
    "thank you",
    "thanks",
    "thanks a lot",
    "thank you so much",
    "thank you very much",
    "thats it",
    "that's it",
    "thats all",
    "that's all",
    "im done",
    "i'm done",
    "we are done",
    "were done",
  ]);

  if (
    exactPhrases.has(normalized)
  ) {
    return true;
  }


  /*
   * Combination phrases.
   *
   * Examples:
   *
   * "thank you thats it"
   * "thats it thank you"
   * "thanks thats all"
   * "thank you im done"
   */
  const hasThanks =
    normalized.includes(
      "thank you"
    ) ||
    normalized.includes(
      "thanks"
    );

  const hasEnding =
    normalized.includes(
      "thats it"
    ) ||
    normalized.includes(
      "that's it"
    ) ||
    normalized.includes(
      "thats all"
    ) ||
    normalized.includes(
      "that's all"
    ) ||
    normalized.includes(
      "im done"
    ) ||
    normalized.includes(
      "i'm done"
    ) ||
    normalized.includes(
      "we are done"
    ) ||
    normalized.includes(
      "were done"
    );

  if (
    hasThanks &&
    hasEnding
  ) {
    return true;
  }


  /*
   * Treat a very short gratitude-only sentence
   * as the end of the voice session.
   *
   * This avoids accidentally ending a session
   * for a real query containing "thank you".
   *
   * Example:
   *
   * "Can you search for the thank you message"
   *
   * should remain a valid search.
   */
  const words =
    normalized.split(" ");

  if (
    hasThanks &&
    words.length <= 5
  ) {
    return true;
  }

  return false;
}


export default function VoiceSearchPanel({
  onVoiceQuery,
  disabled = false,
  searchData = null,
  searchLoading = false,
  searchError = "",
}: VoiceSearchPanelProps) {

  const tokenSource = useMemo(
    () =>
      TokenSource.endpoint(
        "/api/livekit-token"
      ),
    []
  );

  const session = useSession(
    tokenSource,
    {
      agentName: AGENT_NAME,
    }
  );

  const [starting, setStarting] =
    useState(false);

  const [voiceError, setVoiceError] =
    useState("");

  const [dialogOpen, setDialogOpen] =
    useState(false);


  /*
   * --------------------------------------------------
   * START VOICE
   * --------------------------------------------------
   */
  async function startVoice() {

    if (disabled) {
      return;
    }

    setVoiceError("");
    setDialogOpen(true);
    setStarting(true);

    try {

      await session.start();

    } catch (error) {

      console.error(
        "LiveKit session start failed:",
        error
      );

      setVoiceError(
        error instanceof Error
          ? error.message
          : String(error)
      );

    } finally {

      setStarting(false);

    }
  }


  /*
   * --------------------------------------------------
   * STOP VOICE
   * --------------------------------------------------
   */
  async function stopVoice() {

    setVoiceError("");

    try {

      console.log(
        "Ending LiveKit voice session."
      );

      await session.end();

    } catch (error) {

      console.error(
        "LiveKit session end failed:",
        error
      );

      setVoiceError(
        error instanceof Error
          ? error.message
          : String(error)
      );
    }
  }


  return (
    <SessionProvider session={session}>

      <VoiceControls
        starting={starting}
        disabled={disabled}
        onStart={startVoice}
        onStop={stopVoice}
        onVoiceQuery={onVoiceQuery}
        error={voiceError}
        dialogOpen={dialogOpen}
        onOpenDialog={() => setDialogOpen(true)}
        onCloseDialog={() => setDialogOpen(false)}
        searchData={searchData}
        searchLoading={searchLoading}
        searchError={searchError}
      />

      <RoomAudioRenderer />

    </SessionProvider>
  );
}


type VoiceControlsProps = {

  starting: boolean;

  disabled: boolean;

  onStart:
    () => Promise<void>;

  onStop:
    () => Promise<void>;

  onVoiceQuery:
    (query: string) => void;

  error: string;
  dialogOpen: boolean;
  onOpenDialog: () => void;
  onCloseDialog: () => void;
  searchData: VoiceSearchResponse | null;
  searchLoading: boolean;
  searchError: string;
};


function VoiceControls({

  starting,
  disabled,
  onStart,
  onStop,
  onVoiceQuery,
  error,
  dialogOpen,
  onOpenDialog,
  onCloseDialog,
  searchData,
  searchLoading,
  searchError,

}: VoiceControlsProps) {

  const agent =
    useAgent();

  const transcriptions =
    useTranscriptions();

  /*
   * Avoid sending the same final
   * transcription more than once.
   */
  const processedRef =
    useRef<Set<string>>(
      new Set()
    );


  /*
   * Prevent multiple simultaneous
   * session.end() calls.
   */
  const endingRef =
    useRef(false);


  const connected =
    agent.isConnected;

  const failed =
    agent.state === "failed";

  /*
   * Normalize failureReasons to an array.
   *
   * LiveKit may return undefined here,
   * so this avoids the TypeScript error:
   *
   * "agent.failureReasons.length is
   * possibly undefined"
   */
  const failureReasons =
    agent.failureReasons ?? [];

  const failureText =
    failureReasons.length > 0
      ? failureReasons.join(", ")
      : "";


  /*
   * --------------------------------------------------
   * PROCESS FINAL HUMAN TRANSCRIPTS
   * --------------------------------------------------
   *
   * Turn flow:
   *
   * User talks
   *      ↓
   * LiveKit Turn Detector
   *      ↓
   * fillers / pauses tolerated
   *      ↓
   * final transcript
   *      ↓
   * check for end-session phrase
   *      ↓
   *
   * SEARCH QUERY:
   * onVoiceQuery(...)
   *
   * OR
   *
   * "thank you":
   * session.end()
   * --------------------------------------------------
   */

  useEffect(() => {

    if (!connected) {
      return;
    }


    for (
      const transcription
      of transcriptions
    ) {

      /*
       * ----------------------------------------------
       * GET TRANSCRIPT TEXT
       * ----------------------------------------------
       */

      const text =
        transcription.text?.trim();

      if (!text) {
        continue;
      }


      /*
       * ----------------------------------------------
       * ONLY PROCESS HUMAN USER
       * ----------------------------------------------
       *
       * Our authenticated browser participant
       * identity begins with:
       *
       * vespa-manager01-...
       * vespa-intern01-...
       * etc.
       *
       * This prevents the agent's own speech from
       * triggering Vespa searches.
       */

      const participantIdentity =
        transcription
          .participantInfo
          ?.identity || "";


      if (
        !participantIdentity.startsWith(
          "vespa-"
        )
      ) {
        continue;
      }


      /*
       * ----------------------------------------------
       * FINAL TRANSCRIPTS ONLY
       * ----------------------------------------------
       */

      const attributes =
        transcription
          .streamInfo
          ?.attributes || {};


      const isFinal =
        attributes[
          "lk.transcription_final"
        ] === "true";


      if (!isFinal) {
        continue;
      }


      /*
       * ----------------------------------------------
       * DUPLICATE PROTECTION
       * ----------------------------------------------
       */

      const streamId =
        transcription
          .streamInfo
          ?.id || "";


      const key =
        `${participantIdentity}:${streamId}:${text}`;


      if (
        processedRef
          .current
          .has(key)
      ) {
        continue;
      }


      processedRef
        .current
        .add(key);


      console.log(
        "Final voice transcript:",
        text
      );


      /*
       * ----------------------------------------------
       * END SESSION COMMAND
       * ----------------------------------------------
       *
       * Examples:
       *
       * "Thank you."
       * "Thanks."
       * "Thank you, that's it."
       * "That's all, thank you."
       *
       * These are NOT sent to Vespa.
       */

      if (
        isEndSessionPhrase(text)
      ) {

        console.log(
          "Voice end-session phrase detected:",
          text
        );


        /*
         * Prevent another final transcript
         * from trying to close the session
         * at the same time.
         */
        if (
          !endingRef.current
        ) {

          endingRef.current =
            true;


          void onStop()
            .finally(() => {

              endingRef.current =
                false;

            });
        }


        /*
         * Important:
         *
         * Do NOT call:
         *
         * onVoiceQuery(text)
         *
         * because "thank you" is not
         * a search query.
         */
        return;
      }


      /*
       * ----------------------------------------------
       * NORMAL SEARCH QUERY
       * ----------------------------------------------
       *
       * Send the final spoken query to page.tsx.
       *
       * page.tsx:
       *
       * setQuery(...)
       *       ↓
       * POST /search
       *       ↓
       * Vespa hybrid retrieval
       *       ↓
       * RBAC
       *       ↓
       * grounded answer
       *       ↓
       * evidence cards
       */

      console.log(
        "Sending voice query to search:",
        text
      );

      onVoiceQuery(text);
    }

  }, [
    transcriptions,
    connected,
    onVoiceQuery,
    onStop,
  ]);


  const latestUserTranscript = [...transcriptions]
    .reverse()
    .find((item) =>
      (item.participantInfo?.identity || "").startsWith("vespa-") &&
      Boolean(item.text?.trim())
    )?.text?.trim() || "";

  const closeDialog = () => {
    if (connected) {
      void onStop();
    }
    onCloseDialog();
  };

  /*
   * --------------------------------------------------
   * UI
   * --------------------------------------------------
   */

  return (
    <>
      <button
        type="button"
        className="voiceLaunchButton"
        disabled={disabled || starting}
        onClick={connected ? onOpenDialog : onStart}
        title="Open voice search"
        aria-label="Open voice search"
      >
        <span className="voiceLaunchIcon">🎙</span>
        <span>{connected ? "Voice active" : "Voice"}</span>
      </button>

      {dialogOpen && (
        <div className="voiceDialogBackdrop" role="presentation">
          <section
            className="voiceDialog"
            role="dialog"
            aria-modal="true"
            aria-label="VespaSearch voice search"
          >
            <div className="voiceDialogHeader">
              <div>
                <div className="voiceDialogEyebrow">VespaSearch Voice</div>
                <h2>Ask your workspace</h2>
              </div>
              <button
                type="button"
                className="voiceCloseButton"
                onClick={closeDialog}
                aria-label="Close voice search"
              >
                ×
              </button>
            </div>

            <div className="voiceStage">
              <div className={`voiceOrb ${connected ? "voiceOrbActive" : ""}`}>🎙</div>

              {agent.canListen && agent.microphoneTrack ? (
                <div className="voiceVisualizer">
                  <BarVisualizer
                    track={agent.microphoneTrack}
                    state={agent.state}
                    barCount={7}
                  />
                </div>
              ) : null}

              <div
                className={`voiceStatus ${
                  searchLoading
                    ? "voiceStatusSearching"
                    : searchData && !searchLoading
                      ? "voiceStatusReady"
                      : connected
                        ? "voiceStatusListening"
                        : ""
                }`}
              >
                {starting
                  ? "Connecting..."
                  : searchLoading
                    ? "Searching your workspace..."
                    : searchData && !searchLoading
                      ? "Answer ready"
                      : connected && !failed
                        ? "Listening..."
                        : failed
                          ? "Voice connection failed"
                          : "Ready for voice search"}
              </div>
              <div className="voiceHint">Speak naturally. Your final request is searched automatically.</div>
            </div>

            {latestUserTranscript && (
              <div className="voiceConversation">
                <div className="voiceSpeaker">You</div>
                <div className="voiceBubble">“{latestUserTranscript}”</div>
              </div>
            )}

            {searchLoading && (
              <div className="voiceProgress">
                <span className="voiceProgressDot" />
                Searching enterprise knowledge and generating a grounded answer...
              </div>
            )}

            {(error || searchError || failed) && (
              <div className="voiceDialogError">
                {searchError || error || (failureText ? `Voice failed: ${failureText}` : "Voice failed")}
              </div>
            )}

            {searchData && !searchLoading && (
              <div className="voiceResults">
                {searchData.answer && (
                  <article className="voiceAnswerCard">
                    <div className="eyebrow">Grounded answer</div>
                    <div className="voiceAnswer">{searchData.answer}</div>
                  </article>
                )}

                <div className="voiceEvidenceHeader">
                  <span>Retrieved evidence</span>
                  <span>{searchData.results.length} results</span>
                </div>

                <div className="voiceEvidenceList">
                  {searchData.results.length === 0 ? (
                    <div className="voiceEmpty">No results found.</div>
                  ) : searchData.results.map((result, index) => {
                    const restricted = result.access === "restricted";
                    return (
                      <article
                        className={`voiceEvidenceCard ${restricted ? "restrictedCard" : ""}`}
                        key={`${result.doc_id}-${index}`}
                      >
                        <div className="resultTop">
                          <span className="badge">{result.source.replace("_", " ")}</span>
                          <span className="score">{Number(result.relevance || 0).toFixed(3)}</span>
                        </div>
                        <h3>[{index + 1}] {result.title || "Untitled"}</h3>
                        {restricted ? (
                          <div className="restrictedBody">
                            <div className="restrictedLabel">🔒 Limited Role View</div>
                            <p>Content is restricted for your current role.</p>
                            <div className="locationBox">
                              <span>Location</span>
                              <strong>{result.file_location || result.source}</strong>
                            </div>
                          </div>
                        ) : (
                          <>
                            <p className="voiceEvidencePreview">
                              {result.content}
                            </p>
                            {result.file_location && (
                              <div className="fileLocation">Location: {result.file_location}</div>
                            )}
                            {result.url && (
                              <a href={result.url} target="_blank" rel="noreferrer">Open source</a>
                            )}
                          </>
                        )}
                      </article>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="voiceDialogFooter">
              <button
                type="button"
                className="voiceSecondaryButton"
                onClick={closeDialog}
              >
                Close
              </button>
              <button
                type="button"
                className="voicePrimaryButton"
                disabled={disabled || starting}
                onClick={connected ? onStop : onStart}
              >
                {starting ? "Connecting..." : connected ? "■ Stop voice" : "🎙 Start voice"}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
