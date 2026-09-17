# VError D2

VError is a local TypeScript monolith for the Track D2 Prompt Engineering learning slice on an existing VLearn Day 04.

The browser flow is served from `public/index.html` and calls the Fastify API.
The learning orchestrator, answer key, evaluator, retry policy, citation verifier and event writer run on the server.
`GET /api/v1/items/prompt-clarity-01` exposes the public Day card and bounded source catalog, while `GET /api/v1/sources/:sourceId` supports source navigation.
The entry point frames VError as an active-learning layer before the existing Day 04 slides and lecture video, not as a replacement lesson.

## Run

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

The default is `MODEL_MODE=offline`, so the complete flow works without a network or API key.
Set `MODEL_MODE=live`, `OPENAI_API_KEY` and `OPENAI_MODEL` only on the server to enable the bounded D2 Coach wording call.
The live provider is optional and always falls back to the reviewed offline templates.

## Test

```bash
npm test
npm run check
```

The answer key is server-only and is never included in the session response.
The repository contains only short, reviewed excerpts from the captain-provided `Prompt Engineering & Tool Calling.pdf`, not the course data pack.
The demo uses PDF pages 7, 8, 10 and 20 for the prompt-length misconception and records that no transcript segment or video timestamp was available for this PDF.
