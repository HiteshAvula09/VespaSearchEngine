import { NextRequest, NextResponse } from "next/server";
import { AccessToken } from "livekit-server-sdk";
import {
  RoomAgentDispatch,
  RoomConfiguration,
} from "@livekit/protocol";

const BACKEND_API =
  process.env.BACKEND_API_URL ||
  "http://localhost:8000";

const AGENT_NAME =
  process.env.NEXT_PUBLIC_LIVEKIT_AGENT_NAME ||
  "vespa-search-voice";

type AuthenticatedUser = {
  username: string;
  role: string;
};

export async function POST(
  request: NextRequest
) {
  try {
    /*
     * -------------------------------------------------------
     * 1. AUTHENTICATE THE EXISTING VESPASEARCH USER
     * -------------------------------------------------------
     */

    const cookieHeader =
      request.headers.get("cookie") || "";

    const authResponse = await fetch(
      `${BACKEND_API}/auth/me`,
      {
        method: "GET",

        headers: {
          cookie: cookieHeader,
        },

        cache: "no-store",
      }
    );

    if (!authResponse.ok) {
      console.error(
        "LiveKit token request rejected: user not authenticated"
      );

      return NextResponse.json(
        {
          error: "Not authenticated.",
        },
        {
          status: 401,
        }
      );
    }

    const user =
      (await authResponse.json()) as AuthenticatedUser;

    /*
     * -------------------------------------------------------
     * 2. READ REQUEST FROM LIVEKIT TOKEN SOURCE
     * -------------------------------------------------------
     */

    const body =
      await request.json().catch(() => ({}));

    console.log(
      "LiveKit token request body:",
      JSON.stringify(body, null, 2)
    );

    /*
     * -------------------------------------------------------
     * 3. LIVEKIT CONFIGURATION
     * -------------------------------------------------------
     */

    const livekitUrl =
      process.env.LIVEKIT_URL;

    const apiKey =
      process.env.LIVEKIT_API_KEY;

    const apiSecret =
      process.env.LIVEKIT_API_SECRET;

    if (
      !livekitUrl ||
      !apiKey ||
      !apiSecret
    ) {
      console.error(
        "Missing LiveKit environment variables"
      );

      return NextResponse.json(
        {
          error:
            "LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET must be configured.",
        },
        {
          status: 500,
        }
      );
    }

    /*
     * -------------------------------------------------------
     * 4. CREATE A UNIQUE ROOM
     * -------------------------------------------------------
     */

    const roomName =
      body.room_name ||
      body.roomName ||
      `vespa-voice-${Date.now()}`;

    /*
     * -------------------------------------------------------
     * 5. CREATE PARTICIPANT ACCESS TOKEN
     * -------------------------------------------------------
     */

    const token =
      new AccessToken(
        apiKey,
        apiSecret,
        {
          identity:
            `vespa-${user.username}-${Date.now()}`,

          name:
            user.username,

          /*
           * Signed server-side attributes.
           *
           * The browser cannot modify these.
           */
          attributes: {
            "vespa.username":
              user.username,

            "vespa.role":
              user.role,
          },

          ttl: "10m",
        }
      );

    /*
     * -------------------------------------------------------
     * 6. ROOM PERMISSIONS
     * -------------------------------------------------------
     */

    token.addGrant({
      roomJoin: true,

      room:
        roomName,

      canPublish:
        true,

      canSubscribe:
        true,
    });

    /*
     * -------------------------------------------------------
     * 7. EXPLICITLY DISPATCH OUR LIVEKIT AGENT
     * -------------------------------------------------------
     *
     * This is the important part.
     *
     * The room token now explicitly tells LiveKit:
     *
     * "When this room is created, dispatch
     *  vespa-search-voice into it."
     *
     * This avoids depending on room_config being
     * serialized exactly as expected by the frontend SDK.
     */

    token.roomConfig =
      new RoomConfiguration({
        agents: [
          new RoomAgentDispatch({
            agentName: AGENT_NAME,
          }),
        ],
      });

    /*
     * -------------------------------------------------------
     * 8. GENERATE JWT
     * -------------------------------------------------------
     */

    const participantToken =
      await token.toJwt();

    console.log(
      "LiveKit token generated:",
      {
        roomName,
        username:
          user.username,
        role:
          user.role,
        agent:
          AGENT_NAME,
      }
    );

    /*
     * -------------------------------------------------------
     * 9. RETURN STANDARD TOKENSOURCE RESPONSE
     * -------------------------------------------------------
     */

    return NextResponse.json({
      server_url:
        livekitUrl,

      participant_token:
        participantToken,
    });

  } catch (error) {
    console.error(
      "LiveKit token error:",
      error
    );

    return NextResponse.json(
      {
        error:
          "Unable to create LiveKit session.",
      },
      {
        status: 500,
      }
    );
  }
}