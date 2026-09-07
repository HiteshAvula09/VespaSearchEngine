# Vercel

The `frontend` folder is a Next.js application and can be deployed to Vercel.

A deployed Vercel browser cannot call `http://localhost:8000` on your laptop.

For the public demo:
1. deploy FastAPI somewhere reachable over HTTPS, or use a temporary secure tunnel
2. set `NEXT_PUBLIC_API_URL` in Vercel to the HTTPS backend URL
3. add the Vercel origin to backend `CORS_ORIGINS`

Do not try to host the Vespa stateful search engine on Vercel.
