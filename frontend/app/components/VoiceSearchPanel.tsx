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


type VoiceSearchPanelProps = {
  onVoiceQuery: (query: string) => void;
  disabled?: boolean;
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
};


function VoiceControls({

  starting,
  disabled,
  onStart,
  onStop,
  onVoiceQuery,
  error,

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


  /*
   * --------------------------------------------------
   * UI
   * --------------------------------------------------
   */

  return (

    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
      }}
    >


      {/* MICROPHONE BUTTON */}

      <button
        type="button"

        disabled={
          disabled ||
          starting
        }

        onClick={
          connected
            ? onStop
            : onStart
        }

        title={
          connected
            ? "Stop voice search"
            : "Start voice search"
        }

        aria-label={
          connected
            ? "Stop voice search"
            : "Start voice search"
        }

        style={{
          minWidth: "46px",
          height: "38px",

          cursor:
            disabled
              ? "not-allowed"
              : "pointer",
        }}
      >

        {
          starting
            ? "..."
            : connected
              ? "■"
              : "🎙"
        }

      </button>


      {/* AUDIO VISUALIZER */}

      {
        agent.canListen &&
        agent.microphoneTrack && (

          <div
            style={{
              width: "70px",
              height: "30px",
            }}
          >

            <BarVisualizer
              track={
                agent.microphoneTrack
              }
              state={
                agent.state
              }
              barCount={5}
            />

          </div>

        )
      }


      {/* LISTENING */}

      {
        connected &&
        !failed && (

          <span
            style={{
              fontSize: "13px",
              fontWeight: 600,
              opacity: 0.85,
              whiteSpace: "nowrap",
            }}
          >
            🎙 I&apos;m listening...
          </span>

        )
      }


      {/* FAILURE */}

      {
        failed && (

          <span
            style={{
              fontSize: "12px",
              opacity: 0.8,
              maxWidth: "320px",
            }}
          >

            {
              failureText
                ? `Voice failed: ${failureText}`
                : "Voice failed"
            }

          </span>

        )
      }


      {/* ERROR */}

      {
        error && (

          <span
            style={{
              fontSize: "12px",
              maxWidth: "320px",
            }}
          >
            {error}
          </span>

        )
      }

    </div>
  );
}