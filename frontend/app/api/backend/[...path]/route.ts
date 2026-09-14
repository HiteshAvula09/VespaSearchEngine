import { NextRequest, NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL;

type Context = {
  params: Promise<{
    path: string[];
  }>;
};

async function handler(
  request: NextRequest,
  context: Context
) {
  if (!BACKEND_API_URL) {
    return NextResponse.json(
      {
        error: "BACKEND_API_URL is not configured",
      },
      {
        status: 500,
      }
    );
  }

  try {
    const { path } = await context.params;

    const backendPath = path.join("/");

    const incomingUrl = new URL(request.url);

    const targetUrl =
      `${BACKEND_API_URL}/${backendPath}` +
      incomingUrl.search;

    const headers = new Headers();

    const contentType =
      request.headers.get("content-type");

    const accept =
      request.headers.get("accept");

    const cookie =
      request.headers.get("cookie");

    if (contentType) {
      headers.set("content-type", contentType);
    }

    if (accept) {
      headers.set("accept", accept);
    }

    if (cookie) {
      headers.set("cookie", cookie);
    }

    const method = request.method.toUpperCase();

    let body: ArrayBuffer | undefined;

    if (
      method !== "GET" &&
      method !== "HEAD"
    ) {
      const buffer = await request.arrayBuffer();

      if (buffer.byteLength > 0) {
        body = buffer;
      }
    }

    const backendResponse = await fetch(
      targetUrl,
      {
        method,
        headers,
        body,
        cache: "no-store",
      }
    );

    const responseBody =
      await backendResponse.arrayBuffer();

    const responseHeaders = new Headers();

    const responseContentType =
      backendResponse.headers.get(
        "content-type"
      );

    if (responseContentType) {
      responseHeaders.set(
        "content-type",
        responseContentType
      );
    }

    const setCookie =
      backendResponse.headers.get(
        "set-cookie"
      );

    if (setCookie) {
      const cleanedCookie = setCookie.replace(
        /Domain=[^;]+;?/i,
        ""
      );

      responseHeaders.set(
        "set-cookie",
        cleanedCookie
      );
    }

    return new NextResponse(
      responseBody,
      {
        status: backendResponse.status,
        headers: responseHeaders,
      }
    );
  } catch (error) {
    console.error(
      "Backend proxy error:",
      error
    );

    return NextResponse.json(
      {
        error: "Unable to reach backend API",
      },
      {
        status: 502,
      }
    );
  }
}

export async function GET(
  request: NextRequest,
  context: Context
) {
  return handler(request, context);
}

export async function POST(
  request: NextRequest,
  context: Context
) {
  return handler(request, context);
}

export async function PUT(
  request: NextRequest,
  context: Context
) {
  return handler(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: Context
) {
  return handler(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: Context
) {
  return handler(request, context);
}